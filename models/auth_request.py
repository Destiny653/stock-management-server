from datetime import datetime, timedelta
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field, EmailStr

class PasswordResetRequest(Document):
    email: Indexed(EmailStr)
    token: Indexed(str, unique=True)
    status: str = "pending" # pending, completed, expired
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(hours=1))

    class Settings:
        name = "password_reset_requests"
