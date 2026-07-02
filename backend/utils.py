import os
import bcrypt
import hashlib
import secrets
import json
import requests
import re
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken
from enum import Enum
from dataclasses import dataclass, asdict
import pickle
from pathlib import Path
from bloom_filter2 import BloomFilter

# -------- Configuration --------
PEPPER_ENV = os.getenv("PEPPER", "dev-pepper-replace-in-prod")
PEPPER = PEPPER_ENV.encode("utf-8") if isinstance(PEPPER_ENV, str) else PEPPER_ENV

FERNET_MASTER_KEY_ENV = os.getenv("FERNET_MASTER_KEY", None)
MASTER_KEY_PATH = Path("master.key")
BLOOM_PATH = Path("password_bloom_filter.bloom")

# -------- Master Fernet Key (persistent in dev, env in prod) --------
def get_master_fernet_key() -> bytes:
    """
    Returns the master Fernet key.
    Priority:
      1. FERNET_MASTER_KEY environment variable (bytes or str, must be base64 32 bytes)
      2. master.key file (created on first-run in dev)
      3. Otherwise generate a new key and persist
    """
    if FERNET_MASTER_KEY_ENV:
        key = FERNET_MASTER_KEY_ENV.encode() if isinstance(FERNET_MASTER_KEY_ENV, str) else FERNET_MASTER_KEY_ENV
        try:
            Fernet(key)  # validate key
        except ValueError:
            raise ValueError("FERNET_MASTER_KEY is invalid. Must be 32-byte base64.")
        return key

    if MASTER_KEY_PATH.exists():
        return MASTER_KEY_PATH.read_bytes()

    key = Fernet.generate_key()
    MASTER_KEY_PATH.write_bytes(key)
    try:
        MASTER_KEY_PATH.chmod(0o600)
    except Exception:
        pass  # Ignore platform limitations
    return key

MASTER_FERNET_KEY = get_master_fernet_key()
MASTER_FERNET = Fernet(MASTER_FERNET_KEY)

# -------- HIBP Password Check --------
def check_pwned_password(password: str) -> int:
    """
    Checks if the given password has been exposed in a data breach using the
    Have I Been Pwned API (k-anonymity model).

    Returns:
        int: Number of times the password was found in breaches (0 = safe)
    """
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix, suffix = sha1_hash[:5], sha1_hash[5:]
    url = f"https://api.pwnedpasswords.com/range/{prefix}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except Exception as e:
        raise ConnectionError(f"HIBP API error: {e}")

    for line in response.text.splitlines():
        hash_suffix, count = line.split(':')
        if hash_suffix == suffix:
            return int(count)

    return 0

# -------- Encryption Utilities --------
def encrypt_token_with_master(data: bytes) -> bytes:
    return MASTER_FERNET.encrypt(data)

def decrypt_token_with_master(token: bytes) -> bytes | None:
    try:
        return MASTER_FERNET.decrypt(token)
    except InvalidToken:
        return None

# -------- Security / Logging Structures --------
class RiskLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SAFE = "SAFE"

@dataclass
class SecurityEvent:
    timestamp: datetime
    event_type: str
    username: str
    ip_address: str
    risk_level: RiskLevel
    details: dict
    action_taken: str

    def to_json(self) -> str:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["risk_level"] = self.risk_level.value
        return json.dumps(data, indent=2)

# -------- Password / Credential Utilities --------
class CredentialHygieneScanner:
    COMMON_PASSWORDS = {
        "password", "123456", "qwerty", "letmein", "admin",
        "12345678", "abc123", "iloveyou", "123123", "welcome"
    }

    COMMON_PATTERNS = [
        r"(.)\1{2,}",  # repeated character, e.g., "aaa", "111"
        r"1234", r"abcd", r"qwerty", r"password", r"admin"
    ]

    @staticmethod
    def analyze_strength(password: str) -> dict:
        score = 0
        if len(password) >= 12:
            score += 30
        elif len(password) >= 8:
            score += 20
        else:
            score += 10
        if re.search(r"[A-Z]", password): score += 15
        if re.search(r"[a-z]", password): score += 15
        if re.search(r"[0-9]", password): score += 15
        if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password): score += 15
        if password.lower() in CredentialHygieneScanner.COMMON_PASSWORDS:
            score = min(score, 20)
        for pattern in CredentialHygieneScanner.COMMON_PATTERNS:
            if re.search(pattern, password.lower()):
                score = min(score, 30)
        return {"score": min(score, 100)}

    @staticmethod
    def is_strong(password: str) -> bool:
        return CredentialHygieneScanner.analyze_strength(password)["score"] >= 60

class PasswordCrypto:
    @staticmethod
    def hash_password(password: str, rounds: int = 14, pepper: bytes = PEPPER) -> bytes:
        combined = password.encode("utf-8") + pepper
        salt = bcrypt.gensalt(rounds=rounds)
        return bcrypt.hashpw(combined, salt)

    @staticmethod
    def verify_password(password: str, stored_hash: bytes, pepper: bytes = PEPPER) -> bool:
        combined = password.encode("utf-8") + pepper
        return bcrypt.checkpw(combined, stored_hash)

# -------- Bloom Filter for password reuse detection --------
def load_or_create_bloom(path: Path, max_elements: int = 1_000_000, error_rate: float = 0.001) -> BloomFilter:
    if path.exists() and path.stat().st_size > 0:
        try:
            with path.open("rb") as f:
                return pickle.load(f)
        except Exception:
            pass  # ignore broken file, recreate
    bf = BloomFilter(max_elements=max_elements, error_rate=error_rate)
    with path.open("wb") as f:
        pickle.dump(bf, f)
    return bf

pwd_bloom = load_or_create_bloom(BLOOM_PATH)

class PasswordReuseFilter:
    @staticmethod
    def _digest(password: str, pepper: bytes = PEPPER) -> str:
        return hashlib.sha256(pepper + password.encode()).hexdigest()

    @staticmethod
    def add(password: str):
        digest = PasswordReuseFilter._digest(password)
        pwd_bloom.add(digest)
        try:
            with BLOOM_PATH.open("wb") as f:
                pickle.dump(pwd_bloom, f)
        except Exception:
            pass  # ignore persistence errors

    @staticmethod
    def check(password: str) -> bool:
        digest = PasswordReuseFilter._digest(password)
        return digest in pwd_bloom
