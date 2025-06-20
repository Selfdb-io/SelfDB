from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenWithRefresh(Token):
    refresh_token: str

class TokenWithUserInfo(TokenWithRefresh):
    is_superuser: bool
    email: str
    user_id: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str
