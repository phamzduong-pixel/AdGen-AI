import { useCallback, useState } from "react";
import { FiArrowRight, FiAtSign } from "react-icons/fi";
import { Link, useLocation, useNavigate } from "react-router-dom";

import GoogleLoginButton from "../../components/auth/GoogleLoginButton/GoogleLoginButton";
import PasswordInput from "../../components/auth/PasswordInput/PasswordInput";
import useToast from "../../components/ui/Toast/useToast";
import useAuth from "../../hooks/useAuth";
import { login, loginWithGoogle } from "../../services/api/authApi";
import tokenStorage from "../../services/storage/tokenStorage";
import { validateLogin } from "../../utils/authValidation";

import "./Login.css";

function getLoginError(error) {
  if (!error.response) {
    return navigator.onLine
      ? "Backend không phản hồi. Vui lòng thử lại sau."
      : "Bạn đang mất kết nối mạng. Hãy kiểm tra Internet.";
  }
  if (error.response.status === 404) return "Tài khoản không tồn tại.";
  if (error.response.status === 401) return "Mật khẩu không chính xác.";
  if (error.response.status >= 500) {
    return "Hệ thống đang gặp sự cố. Vui lòng thử lại sau.";
  }
  return error.response.data?.detail || "Đăng nhập thất bại. Vui lòng thử lại.";
}

function getGoogleError(error) {
  if (!error.response) {
    return navigator.onLine
      ? "Không kết nối được với AdGen AI để hoàn tất đăng nhập Google."
      : "Bạn đang mất kết nối mạng. Hãy kiểm tra Internet.";
  }
  return (
    error.response.data?.detail ||
    "Đăng nhập Google thất bại. Vui lòng thử lại."
  );
}

function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const { completeLogin } = useAuth();
  const [formData, setFormData] = useState({
    username: location.state?.identifier || "",
    password: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);

  const finishLogin = useCallback(
    async (data) => {
      if (!data?.access_token) {
        throw new Error("Máy chủ không trả về access token.");
      }
      await completeLogin(data.access_token);
      navigate("/chat", { replace: true });
    },
    [completeLogin, navigate],
  );

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: "" }));
    setFormError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isSubmitting || isGoogleSubmitting) return;

    const errors = validateLogin(formData);
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    setIsSubmitting(true);
    setFormError("");
    tokenStorage.removeAccessToken();
    try {
      const data = await login({
        username: formData.username,
        password: formData.password,
      });
      await finishLogin(data);
    } catch (error) {
      tokenStorage.removeAccessToken();
      const message = getLoginError(error);
      if (error.response?.status === 404) {
        setFieldErrors((current) => ({ ...current, username: message }));
      } else if (error.response?.status === 401) {
        setFieldErrors((current) => ({ ...current, password: message }));
      } else {
        setFormError(message);
        toast.error(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleCredential = useCallback(
    async (credential) => {
      if (isGoogleSubmitting || isSubmitting) return;
      setIsGoogleSubmitting(true);
      setFormError("");
      tokenStorage.removeAccessToken();
      try {
        const data = await loginWithGoogle(credential);
        await finishLogin(data);
      } catch (error) {
        tokenStorage.removeAccessToken();
        const message = getGoogleError(error);
        setFormError(message);
        toast.error(message);
      } finally {
        setIsGoogleSubmitting(false);
      }
    },
    [finishLogin, isGoogleSubmitting, isSubmitting, toast],
  );

  const busy = isSubmitting || isGoogleSubmitting;

  return (
    <main className="login-page">
      <section className="login-showcase">
        <div className="login-showcase__content">
          <Link to="/" className="login-brand">
            <span className="login-brand__logo">DG</span>
            <span className="login-brand__name">AdGen AI</span>
          </Link>
          <div className="login-showcase__main">
            <span className="login-showcase__badge">AI Marketing Assistant</span>
            <h1 className="login-showcase__title">
              Biến ý tưởng thành nội dung quảng cáo
              <span> chuyên nghiệp</span>
            </h1>
            <p className="login-showcase__description">
              Tạo nội dung quảng cáo đa nền tảng nhanh chóng, sáng tạo và phù
              hợp với từng chiến dịch marketing.
            </p>
            <div className="login-feature-list">
              {[
                "Tạo nội dung cho Facebook, TikTok và Google Ads",
                "Cá nhân hóa nội dung theo sản phẩm và khách hàng",
                "Lưu và quản lý toàn bộ lịch sử sáng tạo",
              ].map((feature) => (
                <div className="login-feature" key={feature}>
                  <span className="login-feature__icon">✓</span>
                  <span>{feature}</span>
                </div>
              ))}
            </div>
          </div>
          <p className="login-showcase__footer">
            © 2026 AdGen AI. Intelligent Advertising Content.
          </p>
        </div>
        <div className="login-decoration login-decoration--one" />
        <div className="login-decoration login-decoration--two" />
      </section>

      <section className="login-form-section">
        <div className="login-form-wrapper">
          <div className="login-mobile-brand">
            <span className="login-brand__logo">DG</span>
            <span className="login-brand__name">AdGen AI</span>
          </div>
          <div className="login-form-header">
            <span className="login-form-header__eyebrow">Chào mừng trở lại</span>
            <h2 className="login-form-header__title">Đăng nhập</h2>
            <p className="login-form-header__description">
              Tiếp tục hành trình sáng tạo nội dung quảng cáo cùng AdGen AI.
            </p>
          </div>

          <form className="login-form" onSubmit={handleSubmit} noValidate>
            <div className="login-field">
              <label className="login-field__label" htmlFor="username">
                Email hoặc tên đăng nhập
              </label>
              <div
                className={`login-field__control${
                  fieldErrors.username ? " login-field__control--error" : ""
                }`}
              >
                <FiAtSign className="login-field__icon" aria-hidden="true" />
                <input
                  id="username"
                  name="username"
                  type="text"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="Nhập email hoặc tên đăng nhập"
                  autoComplete="username"
                  maxLength={254}
                  disabled={busy}
                  aria-invalid={Boolean(fieldErrors.username)}
                  aria-describedby="username-error"
                />
              </div>
              <p
                id="username-error"
                className="login-field__error"
                aria-live="polite"
              >
                {fieldErrors.username || "\u00a0"}
              </p>
            </div>

            <div className="login-field">
              <div className="login-field__header">
                <label className="login-field__label" htmlFor="password">
                  Mật khẩu
                </label>
                <Link to="/forgot-password" className="login-forgot-password">
                  Quên mật khẩu?
                </Link>
              </div>
              <PasswordInput
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Nhập mật khẩu"
                autoComplete="current-password"
                disabled={busy}
                error={fieldErrors.password}
              />
              <p
                id="password-error"
                className="login-field__error"
                aria-live="polite"
              >
                {fieldErrors.password || "\u00a0"}
              </p>
            </div>

            {formError && (
              <p className="login-error" role="alert">
                {formError}
              </p>
            )}
            <button
              type="submit"
              className="login-submit-button"
              disabled={busy}
            >
              <span>{isSubmitting ? "Đang đăng nhập..." : "Đăng nhập"}</span>
              {!busy && <FiArrowRight aria-hidden="true" />}
            </button>
          </form>

          <div className="login-divider">
            <span />
            <p>Hoặc</p>
            <span />
          </div>
          {isGoogleSubmitting && (
            <p className="login-google-status" role="status">
              Đang xác thực tài khoản Google...
            </p>
          )}
          <GoogleLoginButton
            onCredential={handleGoogleCredential}
            disabled={busy}
          />
          <p className="login-register-link">
            Chưa có tài khoản? <Link to="/register">Đăng ký miễn phí</Link>
          </p>
        </div>
      </section>

    </main>
  );
}

export default Login;
