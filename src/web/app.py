import logging
import os
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for,
    abort, session, flash, send_from_directory, jsonify,
)

from config.settings import (
    FLASK_SECRET_KEY, FLASK_DEBUG, FLASK_HOST, FLASK_PORT,
    CONTENT_DIR, PATHS, LEGACY_NAMESPACES, WIKI_SITE_NAME,
)
from src.parser.wikitext import WikitextParser
from src.db.connection import (
    db_available, get_page_by_slug, get_page_by_id,
    create_page, get_latest_revision, get_revisions,
    add_revision, rollback_to_revision, get_footnotes,
    get_or_create_user, is_autoconfirmed, get_active_protection,
    log_edit_war,
)
from src.security import AbuseFilter, CaptchaManager, APIRateLimiter

logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)
app.secret_key = FLASK_SECRET_KEY
app.config["SITE_NAME"] = WIKI_SITE_NAME

parser = WikitextParser()
captcha = CaptchaManager()
rate_limiter = APIRateLimiter()


# ================================================================
# 輔助函數
# ================================================================

def ns_to_dir(namespace: str) -> str:
    return namespace.capitalize()


def slug_from_title(title: str) -> str:
    return title.replace(" ", "_").lower()


def load_markdown_file(namespace: str, slug: str) -> str | None:
    ns_dir = ns_to_dir(namespace)
    for ext in (".md", ".wiki", ".txt"):
        path = Path(CONTENT_DIR) / ns_dir / f"{slug}{ext}"
        if path.exists():
            return path.read_text(encoding="utf-8")
    return None


def get_article_count() -> int:
    count = 0
    for ns_dir in Path(CONTENT_DIR).iterdir():
        if ns_dir.is_dir():
            count += len(list(ns_dir.glob("*.md")))
    return count


def render_page_content(raw: str, lang="zh-tw", page_id=None) -> dict:
    parser.footnotes = []
    parser.set_lang(lang)
    parser.set_magic("NUMBEROFARTICLES", str(get_article_count()))
    parser.set_magic("REVISIONDAY", datetime.now().strftime("%d"))
    parser.set_magic("REVISIONMONTH", datetime.now().strftime("%m"))

    if page_id:
        rev = get_latest_revision(page_id)
        if rev and rev.get("created_at"):
            dt = rev["created_at"]
            parser.set_magic("REVISIONDAY", dt.strftime("%d"))
            parser.set_magic("REVISIONMONTH", dt.strftime("%m"))

    body_html = parser.parse(raw)
    return {
        "body_html": body_html,
        "footnotes": parser.footnotes,
    }


def detect_namespace(page_path: str):
    if ":" in page_path:
        ns, slug = page_path.split(":", 1)
        return ns, slug
    slug = page_path
    for ns in LEGACY_NAMESPACES:
        if slug.lower().startswith(ns.lower()):
            return ns, slug[len(ns) + 1:]
    return "Guide", slug


# ================================================================
# 認證裝飾器
# ================================================================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("請先登入", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return wrapper


# ================================================================
# 路由
# ================================================================

@app.route("/")
def homepage():
    lang = request.args.get("lang", session.get("lang", "zh-tw"))
    session["lang"] = lang
    parser.set_lang(lang)
    parser.set_magic("NUMBEROFARTICLES", str(get_article_count()))
    parser.set_magic("CURRENTVERSION", "v1.7.0")

    home_raw = load_markdown_file("Guide", "首頁")
    if home_raw:
        rendered = render_page_content(home_raw, lang=lang)
        body = rendered["body_html"]
    else:
        body = ""

    return render_template(
        "page.html",
        title="首頁",
        body_html=body,
        lang=lang,
        article_count=get_article_count(),
        grade=None,
        footnotes=[],
    )


@app.route("/<path:page_path>")
def view_page(page_path):
    lang = request.args.get("lang", session.get("lang", "zh-tw"))
    session["lang"] = lang

    namespace, slug = detect_namespace(page_path)
    slug = slug_from_title(slug)
    raw = load_markdown_file(namespace, slug)

    if raw is None:
        abort(404)

    page = get_page_by_slug(namespace, slug)
    page_id = page["id"] if page else None
    rendered = render_page_content(raw, lang=lang, page_id=page_id)
    protection = get_active_protection(page_id) if page_id else None

    return render_template(
        "page.html",
        title=page_path,
        body_html=rendered["body_html"],
        footnotes=rendered["footnotes"],
        lang=lang,
        protection_level=protection["level"] if protection else None,
        protection_reason=protection.get("reason") if protection else None,
        grade=page.get("grade") if page else None,
    )


@app.route("/edit/<path:page_path>", methods=["GET", "POST"])
@login_required
def edit_page(page_path):
    if ":" not in page_path:
        abort(400)
    namespace, title = page_path.split(":", 1)
    slug = slug_from_title(title)
    raw = load_markdown_file(namespace, slug) or ""

    protection = None
    page = get_page_by_slug(namespace, slug)
    if page:
        protection = get_active_protection(page["id"])
        if protection and protection["level"] == "full" and session.get("role") != "admin":
            flash("此頁面已完全保護，僅管理員可編輯", "error")
            return redirect(url_for("view_page", page_path=page_path))

    if request.method == "POST":
        if protection and protection["level"] == "semi" and not is_autoconfirmed(session["user_id"]):
            flash("此頁面已半保護，需要自動確認用戶權限", "error")
            return redirect(url_for("view_page", page_path=page_path))

        new_body = request.form.get("body", "")
        summary = request.form.get("summary", "")

        abuse = AbuseFilter(
            user_registered_days=0,
            user_edit_count=0,
        )
        abuse_result = abuse.check_edit(new_body, raw)
        if abuse_result:
            flash(f"濫用過濾器攔截：{abuse_result}", "error")
            logger.warning(f"AbuseFilter triggered by user {session.get('username')} on {page_path}")
            return render_template(
                "edit.html",
                title=f"編輯：{page_path}",
                content=new_body,
                page_path=page_path,
                captcha=captcha.generate_challenge(),
            )

        if captcha.requires_captcha(False, namespace in ("Guide", "Map")):
            cid = request.form.get("captcha_id")
            ans = request.form.get("captcha_answer")
            if not cid or not captcha.verify(cid, ans):
                flash("驗證碼錯誤，請重新輸入", "error")
                return render_template(
                    "edit.html",
                    title=f"編輯：{page_path}",
                    content=new_body,
                    page_path=page_path,
                    captcha=captcha.generate_challenge(),
                )

        if not page:
            page_id = create_page(namespace, title, slug)
        else:
            page_id = page["id"]

        add_revision(page_id, session["user_id"], new_body, summary)
        file_path = Path(CONTENT_DIR) / ns_to_dir(namespace) / f"{slug}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(new_body, encoding="utf-8")

        flash("編輯已儲存", "success")
        return redirect(url_for("view_page", page_path=page_path))

    return render_template(
        "edit.html",
        title=f"編輯：{page_path}",
        content=raw,
        page_path=page_path,
    )


@app.route("/history/<path:page_path>")
def page_history(page_path):
    if ":" not in page_path:
        abort(400)
    namespace, title = page_path.split(":", 1)
    slug = slug_from_title(title)
    page = get_page_by_slug(namespace, slug)
    revisions = []
    if page:
        revisions = get_revisions(page["id"])
    return render_template(
        "history.html",
        title=f"版本歷史：{page_path}",
        revisions=revisions,
        page_path=page_path,
    )


@app.route("/rollback/<path:page_path>/<int:revision_id>")
@admin_required
def rollback(page_path, revision_id):
    if ":" not in page_path:
        abort(400)
    namespace, title = page_path.split(":", 1)
    slug = slug_from_title(title)
    page = get_page_by_slug(namespace, slug)
    if not page:
        abort(404)

    success = rollback_to_revision(page["id"], revision_id, session["user_id"])
    if not success:
        flash("回滾失敗：找不到指定修訂版本", "error")
    else:
        flash("回滾完成", "success")
        target_rev = get_latest_revision(page["id"])
        if target_rev:
            file_path = Path(CONTENT_DIR) / ns_to_dir(namespace) / f"{slug}.md"
            file_path.write_text(target_rev["body"], encoding="utf-8")

    return redirect(url_for("page_history", page_path=page_path))


@app.route("/talk/<path:page_path>")
def talk_page(page_path):
    return render_template(
        "talk.html",
        title=f"討論：{page_path}",
        page_title=page_path,
        is_locked=False,
        threads=[],
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if username:
            user = get_or_create_user(username)
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"歡迎回來，{username}", "success")
            return redirect(request.args.get("next") or url_for("homepage"))
        flash("請輸入用戶名稱", "error")
    return render_template("login.html", title="登入")


@app.route("/logout")
def logout():
    session.clear()
    flash("已登出", "info")
    return redirect(url_for("homepage"))


# ================================================================
# API（限流保護）
# ================================================================

@app.route("/api/captcha")
def api_captcha():
    client_ip = request.remote_addr or "unknown"
    if not rate_limiter.is_allowed(f"captcha:{client_ip}"):
        return jsonify({"error": "rate_limited"}), 429
    challenge = captcha.generate_challenge()
    return jsonify(challenge)


@app.route("/api/article-count")
def api_article_count():
    return jsonify({"count": get_article_count()})


@app.route("/api/color/<path:hex_code>")
def api_color_info(hex_code):
    hex_code = hex_code.lstrip("#")
    try:
        rgb = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        return jsonify({"hex": f"#{hex_code}", "rgb": f"rgb{rgb}"})
    except (ValueError, IndexError):
        return jsonify({"error": "invalid hex"}), 400


# ================================================================
# 靜態檔案
# ================================================================

@app.route("/assets/<path:filename>")
def serve_asset(filename):
    return send_from_directory(Path(PATHS.get("maps")).parent, filename)


@app.route("/css/<path:filename>")
def serve_css(filename):
    css_dir = Path(app.static_folder).parent / "css" if app.static_folder else \
              Path(__file__).parent / "css"
    return send_from_directory(str(css_dir), filename)


@app.route("/js/<path:filename>")
def serve_js(filename):
    js_dir = Path(app.static_folder).parent / "js" if app.static_folder else \
             Path(__file__).parent / "js"
    return send_from_directory(str(js_dir), filename)


# ================================================================
# 錯誤處理
# ================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", title="頁面不存在"), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template("base.html", title="權限不足"), 403


@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "請求過於頻繁，請稍後再試"}), 429


# ================================================================
# 健康檢查（Render 需要）
# ================================================================

@app.route("/health")
def health_check():
    db_status = "ok" if db_available() else "degraded"
    return jsonify({"status": "alive", "database": db_status})


# ================================================================
# 應用啟動（延遲 DB 連線，不阻塞啟動）
# ================================================================

def create_app():
    return app


def run():
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    create_app()
    run()
