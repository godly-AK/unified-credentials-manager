"""Versioned authenticated encryption for the stored CSRF session secret."""
import base64
import hashlib
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings


def encryption_key() -> bytes:
    if settings.data_encryption_key:
        key = base64.b64decode(settings.data_encryption_key, validate=True)
        if len(key) != 32:
            raise ValueError("DATA_ENCRYPTION_KEY must encode exactly 32 random bytes.")
        return key
    if settings.app_env != "development":
        raise ValueError("Configure DATA_ENCRYPTION_KEY outside development.")
    # A reproducible local-demo key only. Production must supply a separate key.
    return hashlib.sha256(b"ucm-local-demo-encryption-key-v1").digest()


def encrypt_secret(value: str, context: str) -> str:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(encryption_key()).encrypt(nonce, value.encode(), context.encode())
    return "v1:" + base64.b64encode(nonce + ciphertext).decode()


def decrypt_secret(value: str, context: str) -> str:
    if not value.startswith("v1:"):
        raise ValueError("Unknown ciphertext version.")
    data = base64.b64decode(value[3:], validate=True)
    return AESGCM(encryption_key()).decrypt(data[:12], data[12:], context.encode()).decode()
