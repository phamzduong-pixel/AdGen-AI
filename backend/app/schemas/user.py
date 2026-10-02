from datetime import datetime
from typing import Literal

from app.core.platforms import LEGACY_PLATFORM_TYPES
from app.core.platforms import SUPPORTED_PLATFORM_TYPES
from app.core.platforms import normalize_custom_platform_name
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validate_bcrypt_length(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu không được vượt quá 72 byte")
        return value


class UserLogin(BaseModel):
    username: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_bcrypt_length(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu không được vượt quá 72 byte")
        return value


class GoogleCredential(BaseModel):
    credential: str = Field(min_length=20, max_length=8192)


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    auth_provider: Literal["local", "google"] = "local"
    avatar_url: str | None = None
    email_verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class RegistrationResponse(UserResponse):
    verification_expires_in: int = 600
    resend_after: int = 60
    verification_sent: bool = False


class UserProfileResponse(UserResponse):
    total_conversations: int = 0
    total_saved_contents: int = 0
    total_campaigns: int = 0
    top_platform: str | None = None


class UserUpdate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    email: EmailStr

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value):
        return value.strip() if isinstance(value, str) else value


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator(
        "current_password",
        "new_password",
        "confirm_password",
    )
    @classmethod
    def validate_bcrypt_length(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu không được vượt quá 72 byte")
        return value

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Xác nhận mật khẩu mới không khớp")
        if self.current_password == self.new_password:
            raise ValueError("Mật khẩu mới phải khác mật khẩu hiện tại")
        return self


class UserSettingsUpdate(BaseModel):
    default_platform: str = Field(default="facebook", min_length=1, max_length=50)
    default_platform_name: str | None = Field(default=None, min_length=2, max_length=80)

    @field_validator("default_platform")
    @classmethod
    def validate_default_platform(cls, value):
        if value not in (*SUPPORTED_PLATFORM_TYPES, *LEGACY_PLATFORM_TYPES):
            raise ValueError("Nền tảng mặc định không hợp lệ")
        return value

    @field_validator("default_platform_name", mode="before")
    @classmethod
    def normalize_default_platform_name(cls, value):
        return normalize_custom_platform_name(value)

    @model_validator(mode="after")
    def validate_custom_platform(self):
        if self.default_platform == "other" and not self.default_platform_name:
            raise ValueError("Vui lòng nhập tên nền tảng mặc định")
        return self
    default_tone: Literal[
        "professional",
        "friendly",
        "persuasive",
        "creative",
    ] = "professional"
    default_language: Literal["vi", "en"] = "vi"
    default_length: Literal["short", "medium", "long"] = "medium"
    default_export_format: Literal["markdown", "txt", "pdf"] = "markdown"
    include_timestamps: bool = True


class UserSettingsResponse(UserSettingsUpdate):
    pass


class MessageResponse(BaseModel):
    message: str
