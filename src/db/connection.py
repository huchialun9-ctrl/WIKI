import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

from config.settings import DATABASE

logger = logging.getLogger(__name__)

_pool: Optional[ThreadedConnectionPool] = None
_db_disabled = False


def init_pool(min_conn=1, max_conn=4):
    global _pool, _db_disabled
    if _pool or _db_disabled:
        return
    try:
        host = os.environ.get("WIKI_DB_HOST") or DATABASE.get("host", "localhost")
        port = int(os.environ.get("WIKI_DB_PORT") or DATABASE.get("port", 5432))
        dbname = os.environ.get("WIKI_DB_NAME") or DATABASE.get("dbname")
        user = os.environ.get("WIKI_DB_USER") or DATABASE.get("user")
        password = os.environ.get("WIKI_DB_PASSWORD") or DATABASE.get("password", "")

        if not dbname:
            logger.warning("DB not configured, running in degraded mode")
            _db_disabled = True
            return

        conn_kw = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": password,
            "connect_timeout": 3,
        }
        _pool = ThreadedConnectionPool(min_conn, max_conn, **conn_kw)
        logger.info(f"DB pool ready ({min_conn}-{max_conn}) @ {host}:{port}/{dbname}")
    except psycopg2.Error as e:
        logger.warning(f"DB unavailable, running in degraded mode: {e}")
        _db_disabled = True


def close_pool():
    global _pool, _db_disabled
    if _pool:
        _pool.closeall()
        _pool = None
        _db_disabled = False
        logger.info("DB pool closed")


@contextmanager
def get_conn():
    if not _pool and not _db_disabled:
        init_pool()
    if not _pool:
        raise RuntimeError("Database is not available (degraded mode)")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def db_available() -> bool:
    if _db_disabled:
        return False
    if not _pool:
        init_pool()
    return _pool is not None


# ================================================================
# CRUD
# ================================================================

def get_page_by_slug(namespace: str, slug: str) -> Optional[dict]:
    if not db_available():
        return None
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT p.*, ag.grade
               FROM pages p
               LEFT JOIN article_grades ag ON ag.page_id = p.id
               WHERE p.namespace = %s AND p.slug = %s""",
            (namespace, slug),
        )
        return cur.fetchone()


def get_page_by_id(page_id: int) -> Optional[dict]:
    if not db_available():
        return None
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT p.*, ag.grade
               FROM pages p
               LEFT JOIN article_grades ag ON ag.page_id = p.id
               WHERE p.id = %s""",
            (page_id,),
        )
        return cur.fetchone()


def create_page(namespace: str, title: str, slug: str, is_protected=False) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO pages (namespace, title, slug, is_protected)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (namespace, slug) DO UPDATE SET title = EXCLUDED.title
               RETURNING id""",
            (namespace, title, slug, is_protected),
        )
        return cur.fetchone()[0]


def get_latest_revision(page_id: int) -> Optional[dict]:
    if not db_available():
        return None
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT r.*, u.username AS editor_name
               FROM revisions r
               JOIN users u ON u.id = r.editor_id
               WHERE r.page_id = %s
               ORDER BY r.created_at DESC LIMIT 1""",
            (page_id,),
        )
        return cur.fetchone()


def add_revision(page_id: int, editor_id: int, body: str, summary: str = "") -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO revisions (page_id, editor_id, body, summary)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (page_id, editor_id, body, summary),
        )
        rev_id = cur.fetchone()[0]
        cur.execute("UPDATE pages SET updated_at = NOW() WHERE id = %s", (page_id,))
        cur.execute(
            "UPDATE users SET edit_count = edit_count + 1 WHERE id = %s",
            (editor_id,),
        )
        return rev_id


def get_revisions(page_id: int, limit=50):
    if not db_available():
        return []
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT r.id, r.summary, r.created_at, r.is_rollback,
                      u.username AS editor
               FROM revisions r
               JOIN users u ON u.id = r.editor_id
               WHERE r.page_id = %s
               ORDER BY r.created_at DESC LIMIT %s""",
            (page_id, limit),
        )
        return cur.fetchall()


def rollback_to_revision(page_id: int, revision_id: int, admin_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT body FROM revisions WHERE id = %s AND page_id = %s",
            (revision_id, page_id),
        )
        target = cur.fetchone()
        if not target:
            return False
        cur.execute(
            """INSERT INTO revisions (page_id, editor_id, body, summary, is_rollback)
               VALUES (%s, %s, %s, %s, TRUE)""",
            (page_id, admin_id, target["body"], f"回滾至修訂 #{revision_id}"),
        )
        return True


def get_footnotes(page_id: int):
    if not db_available():
        return []
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT ref_index, source_type, content, url
               FROM footnotes WHERE page_id = %s ORDER BY ref_index""",
            (page_id,),
        )
        return cur.fetchall()


def save_footnotes(page_id: int, notes: list[dict]):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM footnotes WHERE page_id = %s", (page_id,))
        for i, note in enumerate(notes, 1):
            cur.execute(
                """INSERT INTO footnotes (page_id, ref_index, source_type, content, url)
                   VALUES (%s, %s, %s, %s, %s)""",
                (page_id, i, note.get("source_type", "secondary"),
                 note["content"], note.get("url")),
            )


def get_or_create_user(username: str) -> dict:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if user:
            return user
        cur.execute(
            """INSERT INTO users (username, password_hash, role)
               VALUES (%s, '', 'viewer') RETURNING *""",
            (username,),
        )
        return cur.fetchone()


def is_autoconfirmed(user_id: int) -> bool:
    if not db_available():
        return False
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM autoconfirmed_users WHERE id = %s", (user_id,))
        return cur.fetchone() is not None


def get_active_protection(page_id: int) -> Optional[dict]:
    if not db_available():
        return None
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT level, reason, expires_at
               FROM active_page_protections
               WHERE page_id = %s""",
            (page_id,),
        )
        return cur.fetchone()


def log_edit_war(page_id: int, user_id: int) -> dict:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT id, rollback_count, window_start
               FROM edit_war_warnings
               WHERE page_id = %s AND triggered_by = %s
                 AND window_start > NOW() - INTERVAL '1 hour'
                 AND is_escalated = FALSE""",
            (page_id, user_id),
        )
        warning = cur.fetchone()
        if warning:
            count = warning["rollback_count"] + 1
            cur.execute(
                "UPDATE edit_war_warnings SET rollback_count = %s WHERE id = %s",
                (count, warning["id"]),
            )
            escalated = count >= 3
            if escalated:
                cur.execute(
                    "UPDATE edit_war_warnings SET is_escalated = TRUE WHERE id = %s",
                    (warning["id"],),
                )
            return {"count": count, "escalated": escalated}
        else:
            cur.execute(
                """INSERT INTO edit_war_warnings (page_id, triggered_by, rollback_count)
                   VALUES (%s, %s, 1) RETURNING id, rollback_count""",
                (page_id, user_id),
            )
            row = cur.fetchone()
            return {"count": 1, "escalated": False}
