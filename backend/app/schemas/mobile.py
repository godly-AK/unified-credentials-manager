from pydantic import BaseModel

class AppLoginResponse(BaseModel):
    success: bool
    token: str
    username: str

class StorePublicKeyRequest(BaseModel):
    username: str
    public_key_pem: str

class StoreFcmTokenRequest(BaseModel):
    username: str
    fcm_token: str

class ResetChallengeResponse(BaseModel):
    challenge: str

class VerifyResetRequest(BaseModel):
    username: str
    signed_challenge_b64: str
    challenge_b64: str
    new_password: str

class AnomalyNotifyRequest(BaseModel):
    username: str
    title: str
    body: str
    data: dict | None = None
