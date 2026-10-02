import { getUserErrorMessage } from "./apiError.js";

export const getImageActionLabel = ({ referenceFile, sourceAsset }) => (
  referenceFile || sourceAsset ? "Chỉnh sửa ảnh" : "Tạo ảnh quảng cáo"
);

const CODE_MESSAGES = {
  RESOURCE_EXHAUSTED: "Dịch vụ tạo ảnh đang bị giới hạn quota hoặc rate limit. Hãy kiểm tra usage tier/billing rồi thử lại sau.",
  INVALID_ARGUMENT: "Yêu cầu hoặc tham số tạo ảnh không hợp lệ. Vui lòng kiểm tra prompt, tỷ lệ hoặc ảnh tham chiếu.",
  MODEL_NOT_FOUND: "Model tạo ảnh không khả dụng hoặc không được provider nhận diện. Vui lòng kiểm tra cấu hình model.",
  PERMISSION_DENIED: "Provider không cấp quyền cho yêu cầu tạo ảnh. Vui lòng kiểm tra quyền của API key.",
  UNAUTHENTICATED: "API key của provider không xác thực được. Vui lòng kiểm tra cấu hình Gemini.",
  PROVIDER_TIMEOUT: "Dịch vụ tạo ảnh phản hồi quá lâu. Vui lòng thử lại sau.",
  IMAGE_OUTPUT_MISSING: "Provider không trả về ảnh hợp lệ. Vui lòng thử lại sau.",
  PROVIDER_ERROR: "Không thể hoàn tất yêu cầu tạo ảnh từ provider. Vui lòng thử lại sau.",
};

export const getImageGenerationErrorMessage = (error) => {
  const status = error?.response?.status;
  const detail = error?.response?.data?.detail;
  const code = typeof detail === "object" && detail !== null
    ? detail.code
    : error?.response?.data?.code;

  if (code && CODE_MESSAGES[code]) {
    if (code === "PROVIDER_ERROR" && status === 429) {
      return "Dịch vụ tạo ảnh đang bị giới hạn yêu cầu hoặc tài nguyên. Vui lòng thử lại sau.";
    }
    return CODE_MESSAGES[code];
  }

  // Legacy responses used a plain string detail. Preserve only the old,
  // explicit quota markers; an unclassified 429 gets a neutral message.
  if (status === 429) {
    const legacyDetail = typeof detail === "string" ? detail : "";
    if (/quota|rate limit|resource_exhausted/i.test(legacyDetail)) {
      return CODE_MESSAGES.RESOURCE_EXHAUSTED;
    }
    return "Dịch vụ tạo ảnh đang bị giới hạn yêu cầu hoặc tài nguyên. Vui lòng thử lại sau.";
  }
  if (status === 400 || status === 422) return CODE_MESSAGES.INVALID_ARGUMENT;
  if (status === 401) return CODE_MESSAGES.UNAUTHENTICATED;
  if (status === 403) return CODE_MESSAGES.PERMISSION_DENIED;
  if (status === 504) return CODE_MESSAGES.PROVIDER_TIMEOUT;
  if (status === 502 || status === 503) return CODE_MESSAGES.PROVIDER_ERROR;
  return getUserErrorMessage(error, "Không thể tạo ảnh lúc này. Vui lòng thử lại.");
};