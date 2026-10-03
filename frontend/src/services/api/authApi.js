import api from "./axios";

export const register = async ({ username, email, password }) => {
  const response = await api.post("/auth/register", {
    username,
    email,
    password,
  });

  return response.data;
};

export const login = async ({ username, password }) => {
  const formData = new URLSearchParams();

  formData.set("username", username.trim());

  formData.set("password", password);

  const response = await api.post("/auth/login", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  return response.data;
};

export const getGoogleClientId = async () => {
  const response = await api.get("/auth/google/config", { timeout: 5000 });
  return response.data?.client_id || "";
};
export const loginWithGoogle = async (credential) => {
  const response = await api.post("/auth/google", { credential });
  return response.data;
};

export const requestPasswordReset = async (email) => {
  const response = await api.post("/auth/forgot-password", { email });
  return response.data;
};

export const resendPasswordResetCode = requestPasswordReset;

export const verifyPasswordResetCode = async (email, code) => {
  const response = await api.post("/auth/verify-reset-code", { email, code });
  return response.data;
};

export const resetPassword = async (
  resetToken,
  newPassword,
  confirmPassword,
) => {
  const response = await api.post("/auth/reset-password", {
    reset_token: resetToken,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
  return response.data;
};

export const getMe = async () => {
  const response = await api.get("/auth/me");

  return response.data;
};

export const sendVerificationCode = async (email) => {
  const response = await api.post("/auth/send-verification-code", { email });
  return response.data;
};

export const verifyEmail = async (email, code) => {
  const response = await api.post("/auth/verify-email", { email, code });
  return response.data;
};

export const getSessions = async () => {
  const response = await api.get("/auth/sessions");
  return response.data;
};

export const revokeSession = async (sessionId) => {
  const response = await api.delete(`/auth/sessions/${sessionId}`);
  return response.data;
};

export const logoutCurrentSession = async () => {
  const response = await api.post("/auth/logout");
  return response.data;
};

export const logoutAllSessions = async () => {
  const response = await api.post("/auth/logout-all");
  return response.data;
};
