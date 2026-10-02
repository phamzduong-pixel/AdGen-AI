import { useCallback, useState } from "react";
import { FiArrowRight, FiMail, FiShield, FiUser } from "react-icons/fi";
import { Link, useNavigate } from "react-router-dom";

import GoogleLoginButton from "../../components/auth/GoogleLoginButton/GoogleLoginButton";
import PasswordInput from "../../components/auth/PasswordInput/PasswordInput";
import useToast from "../../components/ui/Toast/useToast";
import useAuth from "../../hooks/useAuth";
import { loginWithGoogle, register } from "../../services/api/authApi";
import tokenStorage from "../../services/storage/tokenStorage";
import { validateRegistration } from "../../utils/authValidation";
import { getRegistrationApiError } from "../../utils/registrationError";

import "./Register.css";

function Register() {
  const navigate = useNavigate();
  const toast = useToast();
  const { completeLogin } = useAuth();
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);

  const handleGoogleCredential = useCallback(
    async (credential) => {
      if (isGoogleSubmitting || isSubmitting) return;
      setIsGoogleSubmitting(true);
      setFormError("");
      tokenStorage.removeAccessToken();
      try {
        const data = await loginWithGoogle(credential);
        await completeLogin(data.access_token);
        navigate("/chat", { replace: true });
      } catch (error) {
        tokenStorage.removeAccessToken();
        const message =
          error.response?.data?.detail ||
          "Đăng ký bằng Google thất bại. Vui lòng thử lại.";
        setFormError(message);
        toast.error(message);
      } finally {
        setIsGoogleSubmitting(false);
      }
    },
    [completeLogin, isGoogleSubmitting, isSubmitting, navigate, toast],
  );

  const busy = isSubmitting || isGoogleSubmitting;

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: "" }));
    setFormError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isSubmitting) return;

    const errors = validateRegistration(formData);
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    setIsSubmitting(true);
    setFormError("");
    try {
      await register({
        username: formData.username.trim(),
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
      });
      toast.success("Đăng ký tài khoản thành công! Vui lòng đăng nhập.");
      navigate("/login", {
        replace: true,
        state: { identifier: formData.username.trim() },
      });
    } catch (error) {
      const apiErrors = getRegistrationApiError(error);
      const { form, ...inputErrors } = apiErrors;
      if (Object.keys(inputErrors).length) {
        setFieldErrors((current) => ({ ...current, ...inputErrors }));
      }
      if (form) {
        setFormError(form);
        toast.error(form);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="register-page">
      <section className="register-showcase">
        <div className="register-showcase__content">
          <Link to="/" className="register-brand">
            <span className="register-brand__logo">DG</span>
            <span className="register-brand__name">AdGen AI</span>
          </Link>
          <div className="register-showcase__main">
            <span className="register-showcase__badge">Bắt đầu miễn phí</span>
            <h1 className="register-showcase__title">
              Xây dựng chiến dịch quảng cáo hiệu quả cùng
              <span> trí tuệ nhân tạo</span>
            </h1>
            <p className="register-showcase__description">
              Một trợ lý sáng tạo nội dung thông minh dành cho cá nhân, doanh
              nghiệp và đội ngũ marketing.
            </p>
            <div className="register-statistics">
              <div className="register-statistic">
                <strong>10+</strong>
                <span>Loại nội dung</span>
              </div>
              <div className="register-statistic">
                <strong>24/7</strong>
                <span>Hỗ trợ sáng tạo</span>
              </div>
              <div className="register-statistic">
                <strong>AI</strong>
                <span>Cá nhân hóa</span>
              </div>
            </div>
          </div>
          <p className="register-showcase__footer">
            Tạo nội dung nhanh hơn. Làm marketing thông minh hơn.
          </p>
        </div>
      </section>

      <section className="register-form-section">
        <div className="register-form-wrapper">
          <div className="register-mobile-brand">
            <span className="register-brand__logo">DG</span>
            <span className="register-brand__name">AdGen AI</span>
          </div>
          <div className="register-form-header">
            <span className="register-form-header__eyebrow">Bắt đầu miễn phí</span>
            <h2 className="register-form-header__title">Tạo tài khoản</h2>
            <p className="register-form-header__description">
              Bắt đầu hành trình sáng tạo nội dung quảng cáo cùng AdGen AI.
            </p>
          </div>

          <form className="register-form" onSubmit={handleSubmit} noValidate>
            <div className="register-field">
              <label htmlFor="username">Tên đăng nhập</label>
              <div
                className={`register-field__control${
                  fieldErrors.username ? " register-field__control--error" : ""
                }`}
              >
                <FiUser aria-hidden="true" />
                <input
                  id="username"
                  name="username"
                  type="text"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="Nhập tên đăng nhập"
                  autoComplete="username"
                  maxLength={32}
                  disabled={busy}
                  aria-invalid={Boolean(fieldErrors.username)}
                  aria-describedby="register-username-error"
                />
              </div>
              <p
                id="register-username-error"
                className="register-field__error"
                aria-live="polite"
              >
                {fieldErrors.username || "\u00a0"}
              </p>
            </div>

            <div className="register-field">
              <label htmlFor="email">Email</label>
              <div
                className={`register-field__control${
                  fieldErrors.email ? " register-field__control--error" : ""
                }`}
              >
                <FiMail aria-hidden="true" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="Nhập địa chỉ email"
                  autoComplete="email"
                  maxLength={254}
                  disabled={busy}
                  aria-invalid={Boolean(fieldErrors.email)}
                  aria-describedby="register-email-error"
                />
              </div>
              <p
                id="register-email-error"
                className="register-field__error"
                aria-live="polite"
              >
                {fieldErrors.email || "\u00a0"}
              </p>
            </div>

            <div className="register-field">
              <label htmlFor="password">Mật khẩu</label>
              <PasswordInput
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Tạo mật khẩu"
                autoComplete="new-password"
                disabled={busy}
                error={fieldErrors.password}
              />
              <p
                id="password-error"
                className={`register-field__error${
                  fieldErrors.password ? "" : " register-field__error--hint"
                }`}
                aria-live="polite"
              >
                {fieldErrors.password ||
                  "Mật khẩu cần có ít nhất 8 ký tự."}
              </p>
            </div>

            <div className="register-field">
              <label htmlFor="confirmPassword">Xác nhận mật khẩu</label>
              <PasswordInput
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Nhập lại mật khẩu"
                autoComplete="new-password"
                disabled={busy}
                error={fieldErrors.confirmPassword}
              />
              <p
                id="confirmPassword-error"
                className="register-field__error"
                aria-live="polite"
              >
                {fieldErrors.confirmPassword || "\u00a0"}
              </p>
            </div>

            <p className="register-agreement">
              <FiShield aria-hidden="true" />
              <span>
                Bằng việc đăng ký, bạn đồng ý với Điều khoản sử dụng và Chính
                sách bảo mật của AdGen AI.
              </span>
            </p>
            {formError && (
              <p
                className="register-message register-message--error"
                role="alert"
              >
                {formError}
              </p>
            )}
            <button
              type="submit"
              className="register-submit-button"
              disabled={busy}
            >
              <span>
                {isSubmitting ? "Đang tạo tài khoản..." : "Đăng ký"}
              </span>
              {!isSubmitting && <FiArrowRight aria-hidden="true" />}
            </button>
          </form>

          <div className="register-divider">
            <span />
            <p>Hoặc tiếp tục bằng</p>
            <span />
          </div>
          {isGoogleSubmitting && (
            <p className="register-google-status" role="status">
              Đang xác thực tài khoản Google...
            </p>
          )}
          <GoogleLoginButton
            onCredential={handleGoogleCredential}
            disabled={busy}
          />
          <p className="register-login-link">
            Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
          </p>
        </div>
      </section>
    </main>
  );
}

export default Register;
