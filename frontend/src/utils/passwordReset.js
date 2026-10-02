import { EMAIL_PATTERN } from "./authValidation.js";

const RESET_FLOW_KEY = "adgen_password_reset_flow";

export function maskEmail(email) {
  const [localPart = "", domain = ""] = email.split("@");
  if (!domain) return "";
  const visible = localPart.slice(0, Math.min(2, localPart.length));
  return `${visible}${"*".repeat(Math.max(3, localPart.length - visible.length))}@${domain}`;
}

export function validateResetEmail(email) {
  const normalized = email.trim();
  if (!normalized) return "Vui lòng nhập email.";
  if (!EMAIL_PATTERN.test(normalized)) return "Email chưa đúng định dạng.";
  return "";
}

export function validateResetPasswords(values) {
  const errors = {};
  if (!values.newPassword) {
    errors.newPassword = "Vui lòng nhập mật khẩu mới.";
  } else if (!values.newPassword.trim()) {
    errors.newPassword = "Mật khẩu không được chỉ chứa khoảng trắng.";
  } else if (values.newPassword.length < 8) {
    errors.newPassword = "Mật khẩu phải có ít nhất 8 ký tự.";
  } else if (new TextEncoder().encode(values.newPassword).length > 72) {
    errors.newPassword = "Mật khẩu quá dài.";
  }
  if (!values.confirmPassword) {
    errors.confirmPassword = "Vui lòng xác nhận mật khẩu.";
  } else if (values.newPassword !== values.confirmPassword) {
    errors.confirmPassword = "Mật khẩu xác nhận không khớp.";
  }
  return errors;
}

export function passwordStrength(password) {
  if (!password) return { score: 0, label: "" };
  if (password.length < 8) return { score: 1, label: "Yếu" };
  let score = 1;
  if (password.length >= 12) score += 1;
  if (/[A-Za-z]/.test(password) && /\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;
  const labels = ["", "Yếu", "Trung bình", "Khá", "Mạnh"];
  return { score, label: labels[score] };
}

export function sanitizeOtp(value) {
  return String(value).replace(/\D/g, "").slice(0, 6);
}

export function getPasswordResetError(error, fallback) {
  if (!error?.response) {
    return navigator.onLine
      ? "Backend không phản hồi. Vui lòng thử lại sau."
      : "Bạn đang mất kết nối mạng. Hãy kiểm tra Internet.";
  }
  if (error.response.status >= 500) {
    return (
      error.response.data?.detail ||
      "Dịch vụ tạm thời không khả dụng. Vui lòng thử lại sau."
    );
  }
  const detail = error.response.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

export function startPasswordResetFlow(email, expiresIn, resendAfter) {
  const now = Date.now();
  const flow = {
    email: email.trim().toLowerCase(),
    maskedEmail: maskEmail(email.trim().toLowerCase()),
    updatedAt: now,
    codeExpiresAt: now + expiresIn * 1000,
    resendAt: now + resendAfter * 1000,
  };
  sessionStorage.setItem(RESET_FLOW_KEY, JSON.stringify(flow));
  return flow;
}

export function updatePasswordResetFlow(values) {
  const current = getPasswordResetFlow() || {};
  const next = { ...current, ...values };
  sessionStorage.setItem(RESET_FLOW_KEY, JSON.stringify(next));
  return next;
}

export function getPasswordResetFlow() {
  try {
    const raw = sessionStorage.getItem(RESET_FLOW_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    sessionStorage.removeItem(RESET_FLOW_KEY);
    return null;
  }
}

export function clearPasswordResetFlow() {
  sessionStorage.removeItem(RESET_FLOW_KEY);
}

export function formatCountdown(seconds) {
  const safeSeconds = Math.max(0, seconds);
  const minutes = Math.floor(safeSeconds / 60);
  return `${minutes}:${String(safeSeconds % 60).padStart(2, "0")}`;
}
