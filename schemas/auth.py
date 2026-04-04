from pydantic import BaseModel, EmailStr
from typing import Optional

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ResetStatusResponse(BaseModel):
    status: str # "pending", "completed", "expired"
    message: Optional[str] = None
