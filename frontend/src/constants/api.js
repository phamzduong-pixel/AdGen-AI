const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();

if (!configuredApiUrl) {
  throw new Error("Thiếu biến môi trường VITE_API_URL");
}

let parsedApiUrl;
try {
  parsedApiUrl = new URL(configuredApiUrl);
} catch {
  throw new Error("VITE_API_URL phải là URL hợp lệ");
}

if (!["http:", "https:"].includes(parsedApiUrl.protocol)) {
  throw new Error("VITE_API_URL chỉ hỗ trợ giao thức HTTP hoặc HTTPS");
}

export const API_BASE_URL = configuredApiUrl.replace(/\/+$/, "");
