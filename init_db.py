"""
Render 部署後初始化腳本 — 建立資料庫綱要。
會在每次 deploy 後自動執行（postDeployCommand）。
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import DATABASE
from src.db.connection import get_conn, init_pool, close_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")

SCHEMA_PATH = Path(__file__).parent / "src" / "db" / "schema.sql"


def main():
    if not SCHEMA_PATH.exists():
        logger.error(f"Schema file not found: {SCHEMA_PATH}")
        sys.exit(1)

    try:
        init_pool()
    except Exception as e:
        logger.warning(f"DB not ready yet, skipping: {e}")
        return

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(schema_sql)
        logger.info("Database schema initialized successfully.")

    close_pool()


if __name__ == "__main__":
    main()
