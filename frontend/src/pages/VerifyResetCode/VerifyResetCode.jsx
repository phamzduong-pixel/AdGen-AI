import { useEffect, useState } from "react";
import { FiCheck, FiRefreshCw } from "react-icons/fi";
import { useNavigate } from "react-router-dom";

import OtpInput from "../../components/auth/OtpInput/OtpInput";
import RecoveryLayout from "../../components/auth/RecoveryLayout/RecoveryLayout";
import useToast from "../../components/ui/Toast/useToast";
import {
  resendPasswordResetCode,
  verifyPasswordResetCode,
} from "../../services/api/authApi";
import {
  formatCountdown,
  getPasswordResetError,
  getPasswordResetFlow,
  updatePasswordResetFlow,
} from "../../utils/passwordReset";

import "./VerifyResetCode.css";

function secondsUntil(timestamp, now) {
  return Math.max(0, Math.ceil((timestamp - now) / 1000));
}

function VerifyResetCode() {
  const navigate = useNavigate();
  const toast = useToast();
  const [flow, setFlow] = useState(getPasswordResetFlow);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [now, setNow] = useState(flow?.updatedAt || 0);

  useEffect(() => {
    if (!flow?.email) {
      navigate("/forgot-password", { replace: true });
      return undefined;
    }
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [flow?.email, navigate]);

  if (!flow?.email) return null;

  const codeSeconds = secondsUntil(flow.codeExpiresAt, now);
  const resendSeconds = secondsUntil(flow.resendAt, now);

  const handleVerify = async (event) => {
    event.preventDefault();
    if (isVerifying || code.length !== 6) {
      if (code.length !== 6) setError("Vui lòng nhập đủ 6 chữ số.");
      return;
    }
    setIsVerifying(true);
    setError("");
    try {
      const response = await verifyPasswordResetCode(flow.email, code);
      updatePasswordResetFlow({
        resetToken: response.reset_token,
        resetTokenExpiresAt: Date.now() + response.expires_in * 1000,
      });
      navigate("/reset-password");
    } catch (verifyError) {
      setError(
        getPasswordResetError(
          verifyError,
          "Không thể xác minh mã. Vui lòng thử lại.",
        ),
      );
      setCode("");
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResend = async () => {
    if (isResending || resendSeconds > 0) return;
    setIsResending(true);
    setError("");
    try {
      const response = await resendPasswordResetCode(flow.email);
      const currentTime = Date.now();
      const nextFlow = updatePasswordResetFlow({
        updatedAt: currentTime,
        codeExpiresAt: currentTime + response.expires_in * 1000,
        resendAt: currentTime + response.resend_after * 1000,
        resetToken: undefined,
        resetTokenExpiresAt: undefined,
      });
      setFlow(nextFlow);
      setNow(currentTime);
      setCode("");
      toast.success("Đã gửi mã xác minh mới.");
    } catch (resendError) {
      const message = getPasswordResetError(
        resendError,
        "Không thể gửi lại mã. Vui lòng thử lại.",
      );
      setError(message);
      toast.error(message);
    } finally {
      setIsResending(false);
    }
  };

  return (
    <RecoveryLayout
      title="Nhập mã xác minh"
      description={`Mã gồm 6 chữ số đã được gửi tới ${flow.maskedEmail}.`}
      backTo="/forgot-password"
      backLabel="Dùng email khác"
    >
      <form className="recovery-form" onSubmit={handleVerify} noValidate>
        <div className="recovery-field">
          <label htmlFor="reset-code-0">Mã xác minh</label>
          <OtpInput
            value={code}
            onChange={(nextCode) => {
              setCode(nextCode);
              setError("");
            }}
            disabled={isVerifying}
            error={Boolean(error)}
          />
          <p className="recovery-field__error" aria-live="polite">
            {error || "\u00a0"}
          </p>
        </div>
        <p className="verify-code-timer" role="timer">
          {codeSeconds > 0
            ? `Mã còn hiệu lực ${formatCountdown(codeSeconds)}`
            : "Mã đã hết hạn. Hãy gửi lại mã mới."}
        </p>
        <button
          type="submit"
          className="recovery-primary-button"
          disabled={isVerifying || code.length !== 6 || codeSeconds === 0}
        >
          <FiCheck aria-hidden="true" />
          <span>{isVerifying ? "Đang xác minh..." : "Xác minh"}</span>
        </button>
        <button
          type="button"
          className="verify-resend-button"
          onClick={handleResend}
          disabled={isResending || resendSeconds > 0}
        >
          <FiRefreshCw aria-hidden="true" />
          <span>
            {isResending
              ? "Đang gửi lại..."
              : resendSeconds > 0
                ? `Gửi lại mã sau ${resendSeconds}s`
                : "Gửi lại mã"}
          </span>
        </button>
      </form>
    </RecoveryLayout>
  );
}

export default VerifyResetCode;
