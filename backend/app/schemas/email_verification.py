from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import field_validator


class EmailVerificationRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class VerifyEmailRequest(EmailVerificationRequest):
    code: str = Field(pattern=r"^\d{6}$")


class EmailVerificationResponse(BaseModel):
    message: str
    expires_in: int
    resend_after: int


class VerifyEmailResponse(BaseModel):
    message: str
