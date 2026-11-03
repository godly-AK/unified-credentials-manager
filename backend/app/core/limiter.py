from slowapi import Limiter
from starlette.requests import Request

from app.core.password_policy import DATA_DIR


def client_address(request: Request) -> str:
    return request.client.host if request.client else "local-test-client"


limiter = Limiter(
    key_func=client_address,
    config_filename=str(DATA_DIR / "slowapi.env"),
)
