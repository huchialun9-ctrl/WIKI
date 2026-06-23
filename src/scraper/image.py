import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

import requests
from PIL import Image

from config.settings import PATHS, SCRAPER_USER_AGENT

logger = logging.getLogger(__name__)


class ImageProcessor:
    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
    WEBP_QUALITY = 80

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": SCRAPER_USER_AGENT})

    def download_and_convert(
        self, url: str, subdir: str, filename: Optional[str] = None
    ) -> Optional[str]:
        dest_dir = Path(PATHS.get(subdir, PATHS["maps"]))
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return None

        ext = os.path.splitext(url.split("?")[0])[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            ext = ".png"

        if not filename:
            filename = hashlib.md5(url.encode()).hexdigest()

        temp_path = dest_dir / f"{filename}{ext}"
        with open(temp_path, "wb") as f:
            f.write(resp.content)

        webp_path = dest_dir / f"{filename}.webp"
        try:
            with Image.open(temp_path) as img:
                img = img.convert("RGBA") if img.mode in ("P", "PA") else img
                img.save(webp_path, "WEBP", quality=self.WEBP_QUALITY)
        except Exception as e:
            logger.error(f"WebP conversion failed for {temp_path}: {e}")
            return None
        finally:
            if temp_path.exists():
                temp_path.unlink()

        logger.info(f"Saved and converted: {webp_path}")
        return str(webp_path)
