import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config.settings import (
    STEAM_APP_ID,
    STEAM_WORKSHOP_ID,
    SCRAPER_USER_AGENT,
    SCRAPER_MIN_DELAY,
    SCRAPER_MAX_DELAY,
    PATHS,
)

logger = logging.getLogger(__name__)


class SteamScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": SCRAPER_USER_AGENT})

    def _random_delay(self):
        delay = random.uniform(SCRAPER_MIN_DELAY, SCRAPER_MAX_DELAY)
        time.sleep(delay)

    def fetch_patch_notes(self) -> Optional[dict]:
        url = f"https://store.steampowered.com/news/app/{STEAM_APP_ID}"
        self._random_delay()
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            posts = soup.select(".newsPost")
            if not posts:
                return None
            latest = posts[0]
            return {
                "title": latest.get("title", "").strip(),
                "date": latest.get("date", "").strip(),
                "body": latest.get_text(strip=True)[:2000],
                "source": "steam_news",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
        except requests.RequestException as e:
            logger.error(f"Failed to fetch patch notes: {e}")
            return None

    def fetch_workshop_listings(self, max_pages=3) -> list[dict]:
        listings = []
        for page in range(1, max_pages + 1):
            url = (
                f"https://steamcommunity.com/workshop/browse/"
                f"?appid={STEAM_WORKSHOP_ID}"
                f"&browsesort=subscriptions"
                f"&section=readytouseitems"
                f"&actualsort=trend"
                f"&p={page}"
            )
            self._random_delay()
            try:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for item in soup.select(".workshopItem"):
                    title_el = item.select_one(".workshopItemTitle")
                    author_el = item.select_one(".workshopItemAuthor a")
                    rating_el = item.select_one(".fileRating")
                    preview_el = item.select_one("img.workshopItemPreview")
                    listings.append({
                        "title": title_el.get_text(strip=True) if title_el else "",
                        "author": author_el.get_text(strip=True) if author_el else "",
                        "rating": self._parse_rating(rating_el),
                        "preview_url": preview_el.get("src") if preview_el else "",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    })
            except requests.RequestException as e:
                logger.error(f"Failed to fetch workshop page {page}: {e}")
        return listings

    def _parse_rating(self, el) -> Optional[float]:
        if not el:
            return None
        text = el.get("title", "") or el.get_text(strip=True)
        try:
            return float(text.split("/")[0].strip())
        except (ValueError, IndexError):
            return None

    def run(self) -> dict:
        return {
            "patch_notes": self.fetch_patch_notes(),
            "workshop": self.fetch_workshop_listings(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
