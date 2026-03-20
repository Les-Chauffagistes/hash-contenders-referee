import bcrypt
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

SESSION_DURATION_DAYS = 30


def normalize_username(username: str) -> str:
    return username.strip().lower()


def is_valid_username(username: str) -> bool:
    if not (3 <= len(username) <= 30):
        return False
    return username.replace("_", "").isalnum()


def is_valid_password(password: str) -> bool:
    return len(password) >= 8


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=SESSION_DURATION_DAYS)