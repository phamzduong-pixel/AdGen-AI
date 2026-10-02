export function getRegistrationApiError(error) {
  if (!error?.response) {
    return {
      form: navigator.onLine
        ? "Backend không phản hồi. Vui lòng thử lại sau."
        : "Bạn đang mất kết nối mạng. Hãy kiểm tra Internet.",
    };
  }

  const status = error.response.status;
  const detail = error.response.data?.detail;
  const detailText = typeof detail === "string" ? detail : "";
  const normalizedDetail = detailText.toLowerCase();

  if (normalizedDetail.includes("username")) {
    return { username: "Tên đăng nhập đã tồn tại." };
  }
  if (normalizedDetail.includes("email")) {
    return { email: "Email đã được sử dụng." };
  }
  if (status === 422) {
    return {
      form: "Thông tin đăng ký chưa hợp lệ. Vui lòng kiểm tra lại các trường.",
    };
  }
  if (status >= 500) {
    return {
      form: "Hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
    };
  }
  return {
    form: detailText || "Đăng ký thất bại. Vui lòng thử lại.",
  };
}
