import hashlib
import sqlite3
import unicodedata
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
BLOCKLIST_PATH = DATA_DIR / "compromised_passwords.txt"
HASH_BLOCKLIST_PATH = DATA_DIR / "compromised_sha1.sqlite3"
MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 128


@dataclass(frozen=True)
class PasswordPolicyResult:
    accepted: bool
    errors: list[str] = field(default_factory=list)


def normalize_password(password: str) -> str:
    return unicodedata.normalize("NFC", password)


def load_blocklist() -> set[str]:
    if not BLOCKLIST_PATH.exists():
        return set()
    return {
        line.strip().casefold()
        for line in BLOCKLIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def is_compromised(password: str) -> bool:
    if password.casefold() in load_blocklist():
        return True
    if not HASH_BLOCKLIST_PATH.exists():
        return False
    # SHA-1 is only a lookup key for a public breach corpus. User password
    # verifiers are still independently salted Argon2id hashes.
    digest = hashlib.sha1(password.encode("utf-8")).digest()
    with closing(sqlite3.connect(f"file:{HASH_BLOCKLIST_PATH.as_posix()}?mode=ro", uri=True)) as db:
        return db.execute("SELECT 1 FROM blocked_sha1 WHERE digest = ?", (digest,)).fetchone() is not None


def validate_password(password: str, *, username: str = "", email: str = "") -> PasswordPolicyResult:
    normalized = normalize_password(password)
    errors: list[str] = []

    if len(normalized) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if len(normalized) > MAX_PASSWORD_LENGTH:
        errors.append(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters.")

    folded = normalized.casefold()
    if is_compromised(normalized):
        errors.append("This password is known to be commonly used or compromised.")

    context_words = {username.casefold()}
    if email:
        context_words.add(email.split("@", 1)[0].casefold())
    context_words.discard("")
    if any(len(word) >= 3 and word in folded for word in context_words):
        errors.append("Password must not contain your username or email name.")

    return PasswordPolicyResult(accepted=not errors, errors=errors)
