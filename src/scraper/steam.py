import json
import logging
import random
import re
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
        time.sleep(random.uniform(SCRAPER_MIN_DELAY, SCRAPER_MAX_DELAY))

    def fetch_patch_notes(self) -> Optional[dict]:
        url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
        try:
            resp = self.session.get(
                url,
                params={"appid": STEAM_APP_ID, "count": 5, "maxlength": 1000},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("appnews", {}).get("newsitems", [])
            if not items:
                return None

            for item in items:
                title = item.get("title", "")
                if not title:
                    continue
                return {
                    "title": title.strip(),
                    "date": datetime.fromtimestamp(item["date"]).isoformat(),
                    "body": item.get("contents", "")[:2000],
                    "url": item.get("url", ""),
                    "source": "steam_news_api",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
            return None
        except requests.RequestException as e:
            logger.error(f"Failed to fetch patch notes: {e}")
            return None

    def fetch_workshop_listings(self, max_pages=2) -> list[dict]:
        items_by_id = {}
        for page in range(1, max_pages + 1):
            url = "https://steamcommunity.com/workshop/browse/"
            params = {
                "appid": STEAM_WORKSHOP_ID,
                "browsesort": "subscriptions",
                "section": "readytouseitems",
                "actualsort": "trend",
                "p": page,
            }
            self._random_delay()
            try:
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Build a dict of fileid -> data from all matching links
                for a_tag in soup.find_all("a", href=re.compile(r"sharedfiles/filedetails/\?id=(\d+)")):
                    m = re.search(r"sharedfiles/filedetails/\?id=(\d+)", a_tag["href"])
                    if not m:
                        continue
                    fid = m.group(1)
                    if fid not in items_by_id:
                        items_by_id[fid] = {
                            "title": a_tag.get_text(strip=True) or "",
                            "preview_url": "",
                            "rating": None,
                            "author": "",
                            "publishedfileid": fid,
                            "scraped_at": datetime.now(timezone.utc).isoformat(),
                        }
                    # If this A has an IMG, save the preview URL
                    img = a_tag.find("img")
                    if img and img.get("src"):
                        src = img["src"]
                        # Use the full-res version (remove query params for resize)
                        items_by_id[fid]["preview_url"] = src.split("?")[0]
                    # If this A has text, save it as title
                    txt = a_tag.get_text(strip=True)
                    if txt and not items_by_id[fid]["title"]:
                        items_by_id[fid]["title"] = txt

                # Extract ratings from the page (look for star rating spans)
                for span in soup.find_all("span"):
                    txt = span.get_text(strip=True)
                    m_rate = re.match(r"^(\d+(?:\.\d+)?)\s*★$", txt)
                    if m_rate:
                        rating = float(m_rate.group(1))
                        # Find the associated workshop item by proximity
                        parent = span.find_parent("div", class_=re.compile(r"item|workshop|browse"))
                        if parent:
                            file_link = parent.find("a", href=re.compile(r"sharedfiles/filedetails/\?id=(\d+)"))
                            if file_link:
                                m2 = re.search(r"sharedfiles/filedetails/\?id=(\d+)", file_link["href"])
                                if m2 and m2.group(1) in items_by_id:
                                    items_by_id[m2.group(1)]["rating"] = rating

            except requests.RequestException as e:
                logger.error(f"Failed to fetch workshop page {page}: {e}")

        # Filter: only items with titles, convert to list
        result = [v for v in items_by_id.values() if v["title"]]
        logger.info(f"Scraped {len(result)} workshop items")
        return result

    def run(self) -> dict:
        return {
            "patch_notes": self.fetch_patch_notes(),
            "workshop": self.fetch_workshop_listings(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
