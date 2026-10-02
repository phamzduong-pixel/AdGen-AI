const FLOW_KEY = "adgen_email_verification";

export function maskEmail(email) {
  const [local = "", domain = ""] = String(email).split("@");
  if (!domain) return email;
  const visible = local.slice(0, Math.min(2, local.length));
  return `${visible}${"*".repeat(Math.max(2, local.length - visible.length))}@${domain}`;
}

export function startEmailVerificationFlow(
  email,
  expiresIn = 600,
  resendAfter = 60,
) {
  const now = Date.now();
  const flow = {
    email,
    maskedEmail: maskEmail(email),
    updatedAt: now,
    codeExpiresAt: now + expiresIn * 1000,
    resendAt: now + resendAfter * 1000,
  };
  sessionStorage.setItem(FLOW_KEY, JSON.stringify(flow));
  return flow;
}

export function getEmailVerificationFlow() {
  try {
    return JSON.parse(sessionStorage.getItem(FLOW_KEY)) || null;
  } catch {
    sessionStorage.removeItem(FLOW_KEY);
    return null;
  }
}

export function updateEmailVerificationFlow(changes) {
  const current = getEmailVerificationFlow() || {};
  const next = { ...current, ...changes };
  sessionStorage.setItem(FLOW_KEY, JSON.stringify(next));
  return next;
}

export function clearEmailVerificationFlow() {
  sessionStorage.removeItem(FLOW_KEY);
}
