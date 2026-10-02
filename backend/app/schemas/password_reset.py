from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class ForgotPasswordResponse(BaseModel):
    message: str
    expires_in: int
    resend_after: int


class VerifyResetCodeRequest(ForgotPasswordRequest):
    code: str = Field(pattern=r"^\d{6}$")


class VerifyResetCodeResponse(BaseModel):
    reset_token: str
    expires_in: int


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password", "confirm_password")
    @classmethod
    def validate_password(cls, value):
        if not value.strip():
            raise ValueError("Mật khẩu không được chỉ chứa khoảng trắng")
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu quá dài")
        return value

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Mật khẩu xác nhận không khớp")
        return self
