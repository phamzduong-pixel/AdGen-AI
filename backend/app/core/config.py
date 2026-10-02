from dotenv import load_dotenv
import os
from pathlib import Path
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        return ""
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    sqlite_prefix = "sqlite:///"
    if value.startswith(sqlite_prefix):
        database_path = value.removeprefix(sqlite_prefix)
        if database_path != ":memory:" and not Path(database_path).is_absolute():
            resolved = (BACKEND_DIR / database_path).resolve().as_posix()
            return f"{sqlite_prefix}{resolved}"
    return value


def _upload_dir() -> Path:
    value = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    return value if value.is_absolute() else (BACKEND_DIR / value).resolve()


def _allowed_origins() -> list[str]:
    raw_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = []
    for raw_origin in raw_origins.split(","):
        origin = raw_origin.strip().rstrip("/")
        if not origin:
            continue
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(
                "ALLOWED_ORIGINS chỉ chấp nhận URL http/https hợp lệ"
            )
        if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
            raise RuntimeError(
                "ALLOWED_ORIGINS không được chứa path, query hoặc fragment"
            )
        if origin not in origins:
            origins.append(origin)
    return origins


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} phải là true hoặc false")


class Settings:

    SECRET_KEY = os.getenv("SECRET_KEY", "")

    ALGORITHM = os.getenv(
        "ALGORITHM",
        "HS256",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            60,
        )
    )

    DATABASE_URL = _database_url()

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_IMAGE_MODEL = os.getenv(
        "GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image"
    ).strip()
    IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "gemini").strip().lower()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_IMAGE_MODEL = os.getenv(
        "OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst"
    ).strip()
    IMAGE_GENERATION_TIMEOUT_SECONDS = int(
        os.getenv("IMAGE_GENERATION_TIMEOUT_SECONDS", "120")
    )

    VIDEO_GENERATION_PROVIDER = os.getenv("VIDEO_GENERATION_PROVIDER", "gemini").strip().lower()
    GEMINI_VIDEO_MODEL = os.getenv("GEMINI_VIDEO_MODEL", "veo-3.1-generate-preview").strip()

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "").strip()
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "AdGen AI").strip()
    SMTP_USE_TLS = _env_bool("SMTP_USE_TLS", True)

    PASSWORD_RESET_CODE_EXPIRE_MINUTES = int(
        os.getenv("PASSWORD_RESET_CODE_EXPIRE_MINUTES", "10")
    )
    PASSWORD_RESET_RESEND_SECONDS = int(
        os.getenv("PASSWORD_RESET_RESEND_SECONDS", "60")
    )
    PASSWORD_RESET_MAX_ATTEMPTS = int(
        os.getenv("PASSWORD_RESET_MAX_ATTEMPTS", "5")
    )
    PASSWORD_RESET_EMAIL_HOURLY_LIMIT = int(
        os.getenv("PASSWORD_RESET_EMAIL_HOURLY_LIMIT", "5")
    )
    PASSWORD_RESET_IP_HOURLY_LIMIT = int(
        os.getenv("PASSWORD_RESET_IP_HOURLY_LIMIT", "20")
    )
    EMAIL_VERIFICATION_EXPIRE_MINUTES = int(
        os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", "10")
    )
    EMAIL_VERIFICATION_RESEND_SECONDS = int(
        os.getenv("EMAIL_VERIFICATION_RESEND_SECONDS", "60")
    )
    EMAIL_VERIFICATION_MAX_ATTEMPTS = int(
        os.getenv("EMAIL_VERIFICATION_MAX_ATTEMPTS", "5")
    )

    ALLOWED_ORIGINS = _allowed_origins()

    UPLOAD_DIR = _upload_dir()

    MAX_UPLOAD_SIZE = int(
        os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024))
    )

    MAX_VIDEO_SIZE = int(os.getenv("MAX_VIDEO_SIZE", str(50 * 1024 * 1024)))
    MAX_VIDEO_DURATION_SECONDS = int(os.getenv("MAX_VIDEO_DURATION_SECONDS", "300"))
    MAX_VIDEO_GENERATION_DURATION_SECONDS = int(os.getenv("MAX_VIDEO_GENERATION_DURATION_SECONDS", "8"))
    FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg").strip()
    FFPROBE_BINARY = os.getenv("FFPROBE_BINARY", "ffprobe").strip()
    VIDEO_PROCESS_TIMEOUT_SECONDS = int(os.getenv("VIDEO_PROCESS_TIMEOUT_SECONDS", "120"))
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    def validate(self) -> None:
        missing = []
        invalid_secret_values = {
            "",
            "your_secret_key_here",
            "replace_with_a_long_random_secret",
        }
        if (
            self.SECRET_KEY in invalid_secret_values
            or len(self.SECRET_KEY) < 32
        ):
            missing.append("SECRET_KEY")
        if self.IMAGE_PROVIDER not in {"gemini", "openai"}:
            raise RuntimeError("IMAGE_PROVIDER must be 'gemini' or 'openai'")
        selected_api_key = (
            self.GEMINI_API_KEY
            if self.IMAGE_PROVIDER == "gemini"
            else self.OPENAI_API_KEY
        )
        selected_placeholder = (
            "replace_with_your_gemini_api_key"
            if self.IMAGE_PROVIDER == "gemini"
            else "replace_with_your_openai_api_key"
        )
        if selected_api_key in {"", selected_placeholder}:
            missing.append(
                "GEMINI_API_KEY"
                if self.IMAGE_PROVIDER == "gemini"
                else "OPENAI_API_KEY"
            )
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        if missing:
            raise RuntimeError(
                "Thiếu biến môi trường bắt buộc: " + ", ".join(missing)
            )
        if "*" in self.ALLOWED_ORIGINS:
            raise RuntimeError(
                "ALLOWED_ORIGINS không được dùng '*' khi cho phép credentials"
            )
        if self.MAX_UPLOAD_SIZE <= 0:
            raise RuntimeError("MAX_UPLOAD_SIZE phải lớn hơn 0")
        if self.IMAGE_GENERATION_TIMEOUT_SECONDS <= 0:
            raise RuntimeError("IMAGE_GENERATION_TIMEOUT_SECONDS phải lớn hơn 0")
        if not self.ALLOWED_ORIGINS:
            raise RuntimeError("ALLOWED_ORIGINS phải có ít nhất một origin")
        if self.ENVIRONMENT not in {"development", "test", "production"}:
            raise RuntimeError(
                "ENVIRONMENT phải là development, test hoặc production"
            )
        reset_values = {
            "SMTP_PORT": self.SMTP_PORT,
            "PASSWORD_RESET_CODE_EXPIRE_MINUTES": (
                self.PASSWORD_RESET_CODE_EXPIRE_MINUTES
            ),
            "PASSWORD_RESET_RESEND_SECONDS": self.PASSWORD_RESET_RESEND_SECONDS,
            "PASSWORD_RESET_MAX_ATTEMPTS": self.PASSWORD_RESET_MAX_ATTEMPTS,
            "PASSWORD_RESET_EMAIL_HOURLY_LIMIT": (
                self.PASSWORD_RESET_EMAIL_HOURLY_LIMIT
            ),
            "PASSWORD_RESET_IP_HOURLY_LIMIT": (
                self.PASSWORD_RESET_IP_HOURLY_LIMIT
            ),
            "EMAIL_VERIFICATION_EXPIRE_MINUTES": (
                self.EMAIL_VERIFICATION_EXPIRE_MINUTES
            ),
            "EMAIL_VERIFICATION_RESEND_SECONDS": (
                self.EMAIL_VERIFICATION_RESEND_SECONDS
            ),
            "EMAIL_VERIFICATION_MAX_ATTEMPTS": (
                self.EMAIL_VERIFICATION_MAX_ATTEMPTS
            ),
        }
        invalid_reset_values = [
            name for name, value in reset_values.items() if value <= 0
        ]
        if invalid_reset_values:
            raise RuntimeError(
                "Các cấu hình phải lớn hơn 0: "
                + ", ".join(invalid_reset_values)
            )


settings = Settings()
