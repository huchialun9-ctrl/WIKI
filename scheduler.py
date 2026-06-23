import logging
import subprocess
import sys
import time
from pathlib import Path

import schedule

from config.settings import SCRAPER_INTERVAL_HOURS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("scheduler")


def job():
    logger.info("Starting scheduled scrape...")
    result = subprocess.run(
        [sys.executable, "run_scraper.py"],
        capture_output=True, text=True, cwd=Path(__file__).parent
    )
    if result.returncode == 0:
        logger.info("Scrape completed successfully.")
    else:
        logger.error(f"Scrape failed:\n{result.stderr}")


def main():
    interval = max(SCRAPER_INTERVAL_HOURS, 1)
    schedule.every(interval).hours.do(job)
    logger.info(f"Scheduler started. Running every {interval} hours.")
    logger.info("Press Ctrl+C to stop.")

    job()

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
