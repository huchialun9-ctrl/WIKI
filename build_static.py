"""
靜態站點產生器 — 將 Flask Wiki 匯出為靜態 HTML，
可直接部署至 GitHub Pages (/docs 目錄)。
"""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["WIKI_DEBUG"] = "false"

from flask import url_for
from src.parser.wikitext import WikitextParser
from config.settings import CONTENT_DIR, PATHS

OUTPUT_DIR = Path(__file__).parent / "docs"
STATIC_OUTPUT = OUTPUT_DIR / "static"
ASSETS_OUTPUT = OUTPUT_DIR / "assets"

PAGE_ROUTES = [
    "/",
    "/Guide:%E9%81%8A%E6%88%B2%E6%A9%9F%E5%88%B6",
    "/Map:mansion",
    "/Item:%E5%90%B8%E8%89%B2%E7%AE%A1",
    "/Workshop:viking-dining",
    "/Osaka%EF%BC%88%E6%B6%88%E6%AD%A7%E7%BE%A9%EF%BC%89",
    "/login",
]

STATIC_FILES = [
    ("src/web/static/css/wiki.css", "static/css/wiki.css"),
    ("src/web/static/js/wiki.js", "static/js/wiki.js"),
    ("src/web/static/assets/placeholder.svg", "assets/placeholder.svg"),
]


def clean_output():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "static/css").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "static/js").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "assets").mkdir(parents=True, exist_ok=True)
    print("  Cleaned output directory")


def copy_static_files():
    for src_rel, dst_rel in STATIC_FILES:
        src = Path(__file__).parent / src_rel
        dst = OUTPUT_DIR / dst_rel
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied: {src_rel}")
        else:
            print(f"  WARNING: {src_rel} not found, skipping")


def collect_markdown_pages():
    pages = []
    for ns_dir in sorted(CONTENT_DIR.iterdir()):
        if not ns_dir.is_dir() or ns_dir.name.startswith("."):
            continue
        for md_file in sorted(ns_dir.glob("*.md")):
            slug = md_file.stem.lower()
            ns = ns_dir.name
            page_path = f"{ns}:{slug}"
            pages.append((page_path, md_file))
    return pages


def render_all_pages(application):
    parser = WikitextParser()

    with application.app_context():
        all_pages = [("/", "index.html")]
        all_pages.append(("/login", "login.html"))

        for page_path, md_file in collect_markdown_pages():
            filename = page_path.replace(":", "_").replace(" ", "_") + ".html"
            all_pages.append((f"/{page_path}", filename))

        for route, filename in all_pages:
            try:
                client = application.test_client()
                resp = client.get(route)
                if resp.status_code == 200:
                    html = resp.data.decode("utf-8")
                    filepath = OUTPUT_DIR / filename
                    filepath.write_text(html, encoding="utf-8")
                    print(f"  Rendered: /{route} -> {filename}")
                else:
                    print(f"  ERROR {resp.status_code}: /{route}")
            except Exception as e:
                print(f"  ERROR rendering /{route}: {e}")

        with open(OUTPUT_DIR / "index.html", "r", encoding="utf-8") as f:
            index_html = f.read()
        (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")


def create_gh_pages_config():
    """寫入 _config.yml 讓 GitHub Pages 正確使用 /docs"""
    config = """# GitHub Pages 設定
title: Meccha Chameleon Wiki
description: 塗鴉躲貓貓主題維基百科
baseurl: ""
url: "https://huchialun9-ctrl.github.io/WIKI"
"""
    with open(OUTPUT_DIR / "_config.yml", "w", encoding="utf-8") as f:
        f.write(config)
    print("  Created _config.yml")


def create_readme():
    readme = """# Meccha Chameleon Wiki — 靜態站點

本目錄由 `build_static.py` 自動產生，為 GitHub Pages 靜態站點。

- **Publish Directory**: `docs/`（GitHub Pages 設定）
- **來源專案**: https://github.com/huchialun9-ctrl/WIKI

## 啟動方式

1. 前往 GitHub Repo → Settings → Pages
2. Source 選 **Deploy from a branch**
3. Branch 選 `master`，目錄選 `/docs`
4. 按下 Save
"""
    with open(OUTPUT_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print("  Created README.md for docs/")


def main():
    print("=== Meccha Chameleon Wiki 靜態站點產生器 ===\n")

    print("1. Cleaning output directory...")
    clean_output()

    print("\n2. Copying static files...")
    copy_static_files()

    print("\n3. Creating application...")
    application = create_app()

    print("\n4. Rendering all wiki pages...")
    render_all_pages(application)

    print("\n5. Creating GitHub Pages config...")
    create_gh_pages_config()
    create_readme()

    print(f"\n=== 完成！靜態站點已輸出至 {OUTPUT_DIR} ===")
    print(f"   共 {len(list(OUTPUT_DIR.glob('*.html')))} 頁")
    print("\n   前往 GitHub Repo → Settings → Pages")
    print("   將 Publish Directory 設為 /docs 即可上線。")


if __name__ == "__main__":
    main()
