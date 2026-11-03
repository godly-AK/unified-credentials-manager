from pydantic import BaseModel, Field

class AppLoginResponse(BaseModel):
    success: bool
    token: str
    username: str

class StorePublicKeyRequest(BaseModel):
    username: str = Field(max_length=64)
    public_key_pem: str = Field(max_length=8192)
    current_password: str = Field(max_length=1024)

class ResetChallengeResponse(BaseModel):
    challenge: str

class VerifyResetRequest(BaseModel):
    username: str = Field(max_length=64)
    signed_challenge_b64: str = Field(max_length=1024)
    challenge_b64: str = Field(max_length=128)
    new_password: str = Field(max_length=1024)

class AnomalyNotifyRequest(BaseModel):
    username: str
    title: str
    body: str
    data: dict | None = None
