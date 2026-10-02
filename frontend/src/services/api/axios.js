import axios from "axios";

import { API_BASE_URL } from "../../constants/api";
import tokenStorage from "../storage/tokenStorage";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,

  headers: {
    Accept: "application/json",
  },
});

let isHandlingUnauthorized = false;
let sessionController = new AbortController();

api.interceptors.request.use(
  (config) => {
    const accessToken = tokenStorage.getAccessToken();

    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    if (!config.signal) config.signal = sessionController.signal;

    return config;
  },

  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,

  (error) => {
    if (error.response?.status === 401) {
      const requestUrl = error.config?.url || "";

      const isLoginRequest =
        requestUrl.includes("/auth/login") ||
        requestUrl.includes("/auth/google");

      if (!isLoginRequest && !isHandlingUnauthorized) {
        isHandlingUnauthorized = true;
        sessionController.abort();
        sessionController = new AbortController();
        tokenStorage.removeAccessToken();
        localStorage.removeItem("currentConversationId");
        localStorage.removeItem("currentUser");
        sessionStorage.setItem(
          "adgen_auth_message",
          "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        );
        if (window.location.pathname !== "/login") {
          window.location.replace("/login");
        }
        window.setTimeout(() => {
          isHandlingUnauthorized = false;
        }, 1000);
      }
    }

    return Promise.reject(error);
  },
);

export default api;
