import base64

import pytest
from pydantic import ValidationError

from app.core.config import Settings


PRODUCTION = {
    "app_env": "production",
    "session_cookie_secure": True,
    "data_encryption_key": base64.b64encode(bytes(range(32))).decode(),
    "cors_allow_origins": "https://portal.example.com",
}


def test_production_accepts_secure_configuration():
    settings = Settings(_env_file=None, **PRODUCTION)
    assert settings.allowed_origins == ["https://portal.example.com"]


@pytest.mark.parametrize("override", [
    {"session_cookie_secure": False},
    {"data_encryption_key": None},
    {"data_encryption_key": "not base64"},
    {"data_encryption_key": base64.b64encode(b"short").decode()},
    {"cors_allow_origins": "http://portal.example.com"},
    {"cors_allow_origins": ""},
])
def test_production_rejects_unsafe_configuration(override):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **(PRODUCTION | override))
