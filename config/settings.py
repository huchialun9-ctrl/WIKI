import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE = {
    "host": os.getenv("WIKI_DB_HOST", "localhost"),
    "port": int(os.getenv("WIKI_DB_PORT", 5432)),
    "dbname": os.getenv("WIKI_DB_NAME", "meccha_wiki"),
    "user": os.getenv("WIKI_DB_USER", "wiki_admin"),
    "password": os.getenv("WIKI_DB_PASSWORD", ""),
}

STEAM_APP_ID = 2277090
STEAM_WORKSHOP_ID = 2277090

SCRAPER_INTERVAL_HOURS = 6
SCRAPER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
SCRAPER_MIN_DELAY = 2.0
SCRAPER_MAX_DELAY = 5.0

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CONTENT_DIR = os.path.join(BASE_DIR, "content")

PATHS = {
    "maps": os.path.join(ASSETS_DIR, "maps"),
    "items": os.path.join(ASSETS_DIR, "items"),
    "workshop": os.path.join(ASSETS_DIR, "workshop"),
}

FLASK_SECRET_KEY = os.getenv("WIKI_SECRET_KEY", "dev-secret-change-in-production")
FLASK_DEBUG = os.getenv("WIKI_DEBUG", "true").lower() == "true"
FLASK_HOST = os.getenv("WIKI_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("WIKI_PORT", 5000))

WIKI_SITE_NAME = "Meccha Chameleon Wiki"
WIKI_SITE_URL = os.getenv("WIKI_SITE_URL", "http://127.0.0.1:5000")

LEGACY_NAMESPACES = {
    "Guide": "指南",
    "Map": "地圖",
    "Item": "道具與外觀",
    "Workshop": "工作坊",
}
