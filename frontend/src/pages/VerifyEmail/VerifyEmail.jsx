import { useEffect, useState } from "react";
import { FiCheck, FiRefreshCw } from "react-icons/fi";
import { useNavigate } from "react-router-dom";

import OtpInput from "../../components/auth/OtpInput/OtpInput";
import RecoveryLayout from "../../components/auth/RecoveryLayout/RecoveryLayout";
import useToast from "../../components/ui/Toast/useToast";
import {
  sendVerificationCode,
  verifyEmail,
} from "../../services/api/authApi";
import {
  clearEmailVerificationFlow,
  getEmailVerificationFlow,
  updateEmailVerificationFlow,
} from "../../utils/emailVerification";
import { formatCountdown, getPasswordResetError } from "../../utils/passwordReset";

import "./VerifyEmail.css";

function secondsUntil(timestamp, now) {
  return Math.max(0, Math.ceil((timestamp - now) / 1000));
}

function VerifyEmail() {
  const navigate = useNavigate();
  const toast = useToast();
  const [flow, setFlow] = useState(getEmailVerificationFlow);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [now, setNow] = useState(flow?.updatedAt || 0);

  useEffect(() => {
    if (!flow?.email) {
      navigate("/login", { replace: true });
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
      await verifyEmail(flow.email, code);
      clearEmailVerificationFlow();
      toast.success("Xác minh email thành công");
      navigate("/login", {
        replace: true,
        state: { identifier: flow.email },
      });
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
      const response = await sendVerificationCode(flow.email);
      const currentTime = Date.now();
      const nextFlow = updateEmailVerificationFlow({
        updatedAt: currentTime,
        codeExpiresAt: currentTime + response.expires_in * 1000,
        resendAt: currentTime + response.resend_after * 1000,
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
      title="Xác minh email"
      description={`Nhập mã gồm 6 chữ số đã gửi tới ${flow.maskedEmail}.`}
      backTo="/login"
      backLabel="Quay lại đăng nhập"
    >
      <form className="recovery-form" onSubmit={handleVerify} noValidate>
        <div className="recovery-field">
          <label htmlFor="email-code-0">Mã xác minh</label>
          <OtpInput
            idPrefix="email-code"
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
        <p className="verify-email-timer" role="timer">
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
          <span>{isVerifying ? "Đang xác minh..." : "Xác minh email"}</span>
        </button>
        <button
          type="button"
          className="verify-email-resend"
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

export default VerifyEmail;
