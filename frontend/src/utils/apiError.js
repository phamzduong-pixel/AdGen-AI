const FIELD_LABELS = {
  text: "Nội dung lời thoại",
  raw_script: "Kịch bản",
  voice_id: "Giọng đọc",
  speed: "Tốc độ đọc",
  pitch: "Cao độ",
  message_id: "Mã tin nhắn",
};

const formatPydanticItem = (item) => {
  if (!item) return "";
  if (typeof item === "string") return item;
  if (typeof item === "object") {
    const fieldName = Array.isArray(item.loc)
      ? item.loc[item.loc.length - 1]
      : (item.loc || "");
    const fieldLabel = FIELD_LABELS[fieldName] || fieldName;

    let msg = item.msg || "Dữ liệu không hợp lệ";
    if (item.type === "string_too_short" || item.type === "value_error.missing") {
      msg = "không được để trống";
    } else if (item.type === "string_type") {
      msg = "phải là chuỗi ký tự hợp lệ";
    } else if (item.type === "greater_than_equal" || item.type === "less_than_equal") {
      msg = "vượt quá giới hạn cho phép";
    }

    return fieldLabel ? `${fieldLabel}: ${msg}` : msg;
  }
  return String(item);
};

export const getUserErrorMessage = (error, fallback) => {
  const safeFallback = typeof fallback === "string" ? fallback : "Đã có lỗi xảy ra. Vui lòng thử lại.";

  if (error?.name === "AbortError") return "";

  if (!error?.response) {
    if (!navigator.onLine) {
      return "Bạn đang mất kết nối mạng. Hãy kiểm tra Internet.";
    }
    // Axios timeout: error.code === 'ECONNABORTED'
    if (
      error?.code === "ECONNABORTED" ||
      (error?.message && typeof error.message === "string" && error.message.toLowerCase().includes("timeout"))
    ) {
      return "Yêu cầu mất quá nhiều thời gian. Vui lòng thử lại hoặc kiểm tra kết nối mạng.";
    }
    if (error?.message && typeof error.message === "string" && !error.message.includes("status code")) {
      return error.message;
    }
    return "Máy chủ không phản hồi. Vui lòng thử lại sau.";
  }

  const status = error.response.status;
  if (status === 401) return "Phiên đăng nhập đã hết hạn.";
  if (status === 413) return "Tệp tải lên vượt quá dung lượng cho phép.";
  if (status === 429) return "Dịch vụ AI đang quá tải hoặc đã hết hạn mức. Vui lòng thử lại sau.";
  if (status === 502 || status === 503 || status === 504) {
    return "AdGen AI tạm thời không thể tạo phản hồi. Vui lòng thử lại.";
  }
  if (status >= 500) return "Máy chủ gặp sự cố. Vui lòng thử lại sau.";

  // Handle FastAPI / Pydantic validation errors (422) or client errors (< 500)
  const data = error.response.data;
  if (data) {
    const detail = data.detail;

    // detail as plain string
    if (typeof detail === "string") return detail;

    // detail as array of Pydantic validation error objects: [{type, loc, msg, input, ctx}]
    if (Array.isArray(detail)) {
      const messages = detail.map(formatPydanticItem).filter(Boolean);
      if (messages.length > 0) {
        return messages.join(". ");
      }
    }

    // detail as a single object
    if (detail && typeof detail === "object") {
      if (typeof detail.msg === "string") return detail.msg;
      if (typeof detail.message === "string") return detail.message;
      if (typeof detail.error === "string") return detail.error;
    }

    // fallback to data.message or data.error
    if (typeof data.message === "string") return data.message;
    if (typeof data.error === "string") return data.error;
  }

  return safeFallback;
};

