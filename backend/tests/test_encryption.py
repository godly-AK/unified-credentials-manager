import pytest
from cryptography.exceptions import InvalidTag
from app.core.encryption import encrypt_secret, decrypt_secret


def test_aes_gcm_round_trip_uses_fresh_nonces():
    first = encrypt_secret("session-specific secret", "session/one")
    second = encrypt_secret("session-specific secret", "session/one")
    assert first != second
    assert "session-specific secret" not in first
    assert decrypt_secret(first, "session/one") == "session-specific secret"


def test_aes_gcm_rejects_wrong_context_and_modified_ciphertext():
    encrypted = encrypt_secret("session-specific secret", "session/one")
    with pytest.raises(InvalidTag):
        decrypt_secret(encrypted, "session/two")
    replacement = "A" if encrypted[-5] != "A" else "B"
    with pytest.raises(InvalidTag):
        decrypt_secret(encrypted[:-5] + replacement + encrypted[-4:], "session/one")
