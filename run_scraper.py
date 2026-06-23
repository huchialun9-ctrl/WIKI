import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import ASSETS_DIR, PATHS
from src.scraper import SteamScraper, ImageProcessor
from src.db.connection import init_pool, get_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_scraper")


def save_to_db(patch, listings):
    init_pool()
    with get_conn() as conn:
        cur = conn.cursor()

        if patch:
            cur.execute(
                """INSERT INTO scrape_log (source, payload)
                   VALUES (%s, %s)""",
                ("steam_patch_notes", json.dumps(patch, ensure_ascii=False)),
            )
            logger.info("  Patch notes saved to DB.")

        for item in listings:
            if item.get("rating") and item["rating"] >= 4.0:
                cur.execute(
                    """INSERT INTO workshop_entries
                       (workshop_id, title, creator_name, rating, preview_url)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (workshop_id)
                       DO UPDATE SET rating = EXCLUDED.rating,
                                     preview_url = EXCLUDED.preview_url,
                                     last_synced_at = NOW()""",
                    (
                        hash(item["title"]) % (2**63),
                        item["title"],
                        item.get("author", ""),
                        item["rating"],
                        item.get("preview_url", ""),
                    ),
                )
        logger.info(f"  {len(listings)} workshop entries synced to DB.")


def main():
    scraper = SteamScraper()
    img_proc = ImageProcessor()

    logger.info("=== Meccha Chameleon Wiki Scraper ===")

    logger.info("Fetching patch notes...")
    patch = scraper.fetch_patch_notes()
    if patch:
        logger.info(f"  Latest: {patch['title']}")
    else:
        logger.info("  No new patch notes found.")

    logger.info("Fetching workshop listings...")
    listings = scraper.fetch_workshop_listings(max_pages=2)
    logger.info(f"  Found {len(listings)} items.")

    for item in listings:
        if item.get("preview_url"):
            logger.info(f"  Downloading preview for: {item['title']}")
            safe_name = re.sub(r"[^\w\-]+", "_", item["title"].lower()).strip("_")
            img_proc.download_and_convert(
                item["preview_url"], "workshop",
                filename=safe_name
            )

    try:
        save_to_db(patch, listings)
    except Exception as e:
        logger.error(f"DB save failed: {e}")

    output = {
        "patch_notes": patch,
        "workshop_count": len(listings),
        "workshop_items": listings,
    }

    log_dir = Path(ASSETS_DIR) / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "scrape_result.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"Done. Results saved to {log_path}")


if __name__ == "__main__":
    main()
