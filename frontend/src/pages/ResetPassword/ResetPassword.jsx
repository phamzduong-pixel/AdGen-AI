import { useEffect, useState } from "react";
import { FiCheck } from "react-icons/fi";
import { useNavigate } from "react-router-dom";

import PasswordInput from "../../components/auth/PasswordInput/PasswordInput";
import RecoveryLayout from "../../components/auth/RecoveryLayout/RecoveryLayout";
import useToast from "../../components/ui/Toast/useToast";
import { resetPassword } from "../../services/api/authApi";
import {
  clearPasswordResetFlow,
  getPasswordResetError,
  getPasswordResetFlow,
  passwordStrength,
  validateResetPasswords,
} from "../../utils/passwordReset";

import "./ResetPassword.css";

function ResetPassword() {
  const navigate = useNavigate();
  const toast = useToast();
  const [flow] = useState(getPasswordResetFlow);
  const [values, setValues] = useState({
    newPassword: "",
    confirmPassword: "",
  });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const strength = passwordStrength(values.newPassword);

  useEffect(() => {
    if (
      !flow?.resetToken ||
      !flow?.resetTokenExpiresAt ||
      flow.resetTokenExpiresAt <= Date.now()
    ) {
      clearPasswordResetFlow();
      navigate("/forgot-password", { replace: true });
    }
  }, [flow, navigate]);

  if (
    !flow?.resetToken ||
    !flow?.resetTokenExpiresAt
  ) {
    return null;
  }

  const handleChange = (event) => {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: "" }));
    setFormError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isSubmitting) return;
    const validationErrors = validateResetPasswords(values);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length) return;

    setIsSubmitting(true);
    setFormError("");
    try {
      await resetPassword(
        flow.resetToken,
        values.newPassword,
        values.confirmPassword,
      );
      clearPasswordResetFlow();
      toast.success("Mật khẩu đã được cập nhật thành công.");
      navigate("/login", {
        replace: true,
        state: { identifier: flow.email },
      });
    } catch (resetError) {
      const message = getPasswordResetError(
        resetError,
        "Không thể cập nhật mật khẩu. Vui lòng thử lại.",
      );
      setFormError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <RecoveryLayout
      title="Tạo mật khẩu mới"
      description="Chọn mật khẩu mới an toàn cho tài khoản AdGen AI của bạn."
      backTo="/forgot-password"
      backLabel="Bắt đầu lại"
    >
      <form className="recovery-form" onSubmit={handleSubmit} noValidate>
        <div className="recovery-field">
          <label htmlFor="newPassword">Mật khẩu mới</label>
          <PasswordInput
            id="newPassword"
            name="newPassword"
            value={values.newPassword}
            onChange={handleChange}
            placeholder="Nhập mật khẩu mới"
            autoComplete="new-password"
            disabled={isSubmitting}
            error={errors.newPassword}
          />
          <p
            id="newPassword-error"
            className="recovery-field__error"
            aria-live="polite"
          >
            {errors.newPassword || "\u00a0"}
          </p>
          <div
            className="password-strength"
            aria-label={
              strength.label ? `Độ mạnh mật khẩu: ${strength.label}` : undefined
            }
          >
            <div className="password-strength__bars" aria-hidden="true">
              {[1, 2, 3, 4].map((level) => (
                <span
                  key={level}
                  className={
                    strength.score >= level ? "password-strength__bar--on" : ""
                  }
                />
              ))}
            </div>
            <span>{strength.label || "Mật khẩu cần có ít nhất 8 ký tự."}</span>
          </div>
        </div>
        <div className="recovery-field">
          <label htmlFor="confirmPassword">Xác nhận mật khẩu mới</label>
          <PasswordInput
            id="confirmPassword"
            name="confirmPassword"
            value={values.confirmPassword}
            onChange={handleChange}
            placeholder="Nhập lại mật khẩu mới"
            autoComplete="new-password"
            disabled={isSubmitting}
            error={errors.confirmPassword}
          />
          <p
            id="confirmPassword-error"
            className="recovery-field__error"
            aria-live="polite"
          >
            {errors.confirmPassword || "\u00a0"}
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
          <FiCheck aria-hidden="true" />
          <span>
            {isSubmitting ? "Đang cập nhật..." : "Cập nhật mật khẩu"}
          </span>
        </button>
      </form>
    </RecoveryLayout>
  );
}

export default ResetPassword;
