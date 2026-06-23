import hashlib
import hmac
import logging
import os
import random
import string
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CHALLENGE_EXPIRY_SECONDS = 300


class CaptchaManager:
    def __init__(self, secret_key: str = ""):
        self._secret = secret_key or os.urandom(16).hex()
        self._challenges = {}

    def _make_challenge_id(self) -> str:
        return hashlib.sha256(os.urandom(32)).hexdigest()[:16]

    def generate_challenge(self) -> dict:
        a = random.randint(1, 50)
        b = random.randint(1, 50)
        op = random.choice(["+", "-"])
        if op == "-" and a < b:
            a, b = b, a
        answer = a + b if op == "+" else a - b
        cid = self._make_challenge_id()
        self._challenges[cid] = {
            "answer": answer,
            "expires_at": datetime.now(timezone.utc).timestamp() + CHALLENGE_EXPIRY_SECONDS,
        }
        return {
            "challenge_id": cid,
            "question": f"{a} {op} {b} = ?",
        }

    def verify(self, challenge_id: str, answer: str) -> bool:
        record = self._challenges.pop(challenge_id, None)
        if not record:
            return False
        if datetime.now(timezone.utc).timestamp() > record["expires_at"]:
            return False
        try:
            return int(answer.strip()) == record["answer"]
        except ValueError:
            return False

    def requires_captcha(self, is_anonymous: bool, is_core_page: bool) -> bool:
        return is_anonymous or is_core_page
