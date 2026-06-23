import logging
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

ALLOWED_DOMAINS = {
    "steamcommunity.com",
    "steampowered.com",
    "opencode.ai",
    "github.com",
    "creativecommons.org",
}

EXTERNAL_LINK_RE = re.compile(
    r'https?://(?:[-\w.]|%[\da-fA-F]{2})+[^\s<>"\'(){}|\\^`[\]]*',
)


class AbuseFilter:
    def __init__(self, user_registered_days: int = 0, user_edit_count: int = 0):
        self.user_registered_days = user_registered_days
        self.user_edit_count = user_edit_count

    @staticmethod
    def is_allowed_domain(url: str) -> bool:
        for domain in ALLOWED_DOMAINS:
            if domain in url:
                return True
        return False

    @property
    def is_new_user(self) -> bool:
        return self.user_registered_days < 3

    def check_external_links(self, new_body: str, old_body: str) -> Optional[str]:
        if not self.is_new_user:
            return None
        links = EXTERNAL_LINK_RE.findall(new_body)
        for link in links:
            if not self.is_allowed_domain(link):
                logger.warning(
                    f" AbuseFilter: blocked external link to {link[:60]}... "
                    f"(user age: {self.user_registered_days}d)"
                )
                return (
                    f"新用戶禁止添加非授權外部連結：{link[:80]}。"
                    f"允許的網域：{', '.join(sorted(ALLOWED_DOMAINS))}"
                )
        return None

    def check_blanking(self, new_body: str, old_body: str) -> Optional[str]:
        if not old_body:
            return None
        old_len = len(old_body)
        new_len = len(new_body)
        if old_len > 0 and new_len < old_len * 0.2:
            logger.warning(
                f" AbuseFilter: detected page blanking "
                f"({new_len}/{old_len} chars retained)"
            )
            return (
                "本次編輯將刪除超過 80% 的條目內容，"
                "系統已自動拒絕。如確需清空頁面，請於編輯摘要說明理由。"
            )
        return None

    def check_edit(self, new_body: str, old_body: str) -> Optional[str]:
        result = self.check_external_links(new_body, old_body)
        if result:
            return result
        result = self.check_blanking(new_body, old_body)
        if result:
            return result
        return None
