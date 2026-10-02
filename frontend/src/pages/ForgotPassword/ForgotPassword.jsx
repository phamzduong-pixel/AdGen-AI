import { useState } from "react";
import { FiArrowRight, FiMail } from "react-icons/fi";
import { useNavigate } from "react-router-dom";

import RecoveryLayout from "../../components/auth/RecoveryLayout/RecoveryLayout";
import useToast from "../../components/ui/Toast/useToast";
import { requestPasswordReset } from "../../services/api/authApi";
import {
  getPasswordResetError,
  startPasswordResetFlow,
  validateResetEmail,
} from "../../utils/passwordReset";

function ForgotPassword() {
  const navigate = useNavigate();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isSubmitting) return;
    const emailError = validateResetEmail(email);
    setError(emailError);
    if (emailError) return;

    setIsSubmitting(true);
    setFormError("");
    try {
      const normalizedEmail = email.trim().toLowerCase();
      const response = await requestPasswordReset(normalizedEmail);
      startPasswordResetFlow(
        normalizedEmail,
        response.expires_in,
        response.resend_after,
      );
      toast.info(response.message);
      navigate("/verify-reset-code");
    } catch (requestError) {
      const message = getPasswordResetError(
        requestError,
        "Không thể gửi mã xác minh. Vui lòng thử lại.",
      );
      setFormError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <RecoveryLayout
      title="Quên mật khẩu?"
      description="Nhập email đã đăng ký để nhận mã xác minh."
    >
      <form className="recovery-form" onSubmit={handleSubmit} noValidate>
        <div className="recovery-field">
          <label htmlFor="reset-email">Email</label>
          <div
            className={`recovery-field__control${
              error ? " recovery-field__control--error" : ""
            }`}
          >
            <FiMail aria-hidden="true" />
            <input
              id="reset-email"
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setError("");
                setFormError("");
              }}
              placeholder="Nhập địa chỉ email"
              autoComplete="email"
              maxLength={254}
              disabled={isSubmitting}
              aria-invalid={Boolean(error)}
              aria-describedby="reset-email-error"
              autoFocus
            />
          </div>
          <p
            id="reset-email-error"
            className="recovery-field__error"
            aria-live="polite"
          >
            {error || "\u00a0"}
          </p>
        </div>
        {formError && (
          <p className="recovery-form__error" role="alert">
            {formError}
          </p>
        )}
        <button
          type="submit"
          className="recovery-primary-button"
          disabled={isSubmitting}
        >
          <span>{isSubmitting ? "Đang gửi mã..." : "Gửi mã xác minh"}</span>
          {!isSubmitting && <FiArrowRight aria-hidden="true" />}
        </button>
      </form>
    </RecoveryLayout>
  );
}

export default ForgotPassword;
