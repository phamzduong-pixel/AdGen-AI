import html
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


class EmailConfigurationError(RuntimeError):
    pass


class EmailDeliveryError(RuntimeError):
    pass


class EmailOTPProvider:
    def ensure_configured(self) -> None:
        required = {
            "SMTP_HOST": settings.SMTP_HOST,
            "SMTP_USERNAME": settings.SMTP_USERNAME,
            "SMTP_PASSWORD": settings.SMTP_PASSWORD,
            "SMTP_FROM_EMAIL": settings.SMTP_FROM_EMAIL,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise EmailConfigurationError(
                "Gửi email chưa được cấu hình: " + ", ".join(missing)
            )
        if "\n" in settings.SMTP_FROM_NAME or "\r" in settings.SMTP_FROM_NAME:
            raise EmailConfigurationError("SMTP_FROM_NAME không hợp lệ")

    def send_code(
        self,
        recipient: str,
        code: str,
        expires_minutes: int,
    ) -> None:
        self.ensure_configured()
        from_name = settings.SMTP_FROM_NAME or "AdGen AI"
        message = EmailMessage()
        message["Subject"] = f"{from_name} – Mã xác minh đặt lại mật khẩu"
        message["From"] = f"{from_name} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = recipient
        message.set_content(
            (
                f"Mã xác minh AdGen AI của bạn là: {code}\n"
                f"Mã có hiệu lực trong {expires_minutes} phút.\n"
                "Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này."
            )
        )
        safe_name = html.escape(from_name)
        message.add_alternative(
            f"""
            <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;
                        color:#1f2937">
              <div style="padding:24px;background:#4f46e5;color:white;
                          border-radius:14px 14px 0 0">
                <strong style="font-size:22px">{safe_name}</strong>
              </div>
              <div style="padding:28px;border:1px solid #e5e7eb;
                          border-top:0;border-radius:0 0 14px 14px">
                <h1 style="font-size:20px;margin:0 0 12px">
                  Mã xác minh đặt lại mật khẩu
                </h1>
                <p style="color:#6b7280">Nhập mã sau vào AdGen AI:</p>
                <div style="font-size:34px;font-weight:700;letter-spacing:9px;
                            color:#4f46e5;margin:24px 0">{code}</div>
                <p>Mã có hiệu lực trong <strong>{expires_minutes} phút</strong>.</p>
                <p style="color:#6b7280;font-size:13px">
                  Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này.
                  Không chia sẻ mã này với bất kỳ ai.
                </p>
              </div>
            </div>
            """,
            subtype="html",
        )
        self._deliver(message)

    def send_verification_code(
        self,
        recipient: str,
        code: str,
        expires_minutes: int,
    ) -> None:
        self.ensure_configured()
        from_name = settings.SMTP_FROM_NAME or "AdGen AI"
        safe_name = html.escape(from_name)
        message = EmailMessage()
        message["Subject"] = f"{from_name} – Xác minh địa chỉ email"
        message["From"] = f"{from_name} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = recipient
        message.set_content(
            (
                f"Mã xác minh email AdGen AI của bạn là: {code}\n"
                f"Mã có hiệu lực trong {expires_minutes} phút.\n"
                "Nếu bạn không tạo tài khoản này, hãy bỏ qua email."
            )
        )
        message.add_alternative(
            f"""
            <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;
                        color:#1f2937">
              <div style="padding:24px;background:#4f46e5;color:white;
                          border-radius:14px 14px 0 0">
                <strong style="font-size:22px">{safe_name}</strong>
              </div>
              <div style="padding:28px;border:1px solid #e5e7eb;
                          border-top:0;border-radius:0 0 14px 14px">
                <h1 style="font-size:20px;margin:0 0 12px">
                  Xác minh địa chỉ email
                </h1>
                <p style="color:#6b7280">Nhập mã sau vào AdGen AI:</p>
                <div style="font-size:34px;font-weight:700;letter-spacing:9px;
                            color:#4f46e5;margin:24px 0">{code}</div>
                <p>Mã có hiệu lực trong <strong>{expires_minutes} phút</strong>.</p>
                <p style="color:#6b7280;font-size:13px">
                  Nếu bạn không tạo tài khoản AdGen AI này, hãy bỏ qua email.
                  Không chia sẻ mã này với bất kỳ ai.
                </p>
              </div>
            </div>
            """,
            subtype="html",
        )
        self._deliver(message)

    def _deliver(self, message: EmailMessage) -> None:
        try:
            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=15,
            ) as smtp:
                smtp.ehlo()
                if settings.SMTP_USE_TLS:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                smtp.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD.replace(" ", ""),
                )
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            raise EmailDeliveryError(
                "Không thể gửi email xác minh"
            ) from error


email_provider = EmailOTPProvider()
