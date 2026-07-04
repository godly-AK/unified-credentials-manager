from pydantic import BaseModel

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None
    ip_address: str | None = None

class LoginRequest(BaseModel):
    username: str
    password: str
    ip_address: str | None = None

class PasswordChangeRequest(BaseModel):
    username: str
    new_password: str

class WebResponse(BaseModel):
    success: bool
    data: dict | None = None
    message: str
