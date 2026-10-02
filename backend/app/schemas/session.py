from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: str
    device_name: str
    browser: str
    ip_address: str | None
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime
    is_current: bool


class LogoutResponse(BaseModel):
    message: str
