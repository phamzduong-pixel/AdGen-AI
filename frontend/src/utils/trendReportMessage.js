const ENGLISH_TREND_MESSAGE = /^(no |unable |failed |not configured|insufficient |external |unsupported |invalid |forbidden |not found )/i;

export const presentTrendMessage = (value, fallback = "Không có thêm thông tin.") => {
  const message = String(value || "").trim();
  if (!message) return fallback;
  if (/^No retrieval collectors are configured/i.test(message)) return "Chưa cấu hình nguồn thu thập dữ liệu xu hướng, nên hệ thống chưa thể thu thập dữ liệu mới cho chủ đề này.";
  if (/^External retrieval (was not usable|is unavailable)/i.test(message)) return "Không thể sử dụng nguồn dữ liệu xu hướng bên ngoài. Hiện chưa có dữ liệu mới từ nguồn đáng tin cậy để hiển thị.";
  if (/^Insufficient evidence/i.test(message)) return "Chưa có đủ bằng chứng hoặc dữ liệu phù hợp từ nguồn để đưa ra kết luận.";
  if (/^No fresh source-backed/i.test(message)) return "Hiện chưa có dữ liệu hoặc số liệu mới từ nguồn đáng tin cậy để hiển thị.";
  if (/^External search is not configured/i.test(message)) return "Chưa cấu hình nguồn tìm kiếm dữ liệu xu hướng bên ngoài.";
  if (/^External search is temporarily unavailable/i.test(message)) return "Nguồn tìm kiếm dữ liệu xu hướng đang tạm thời không khả dụng. Vui lòng thử lại sau.";
  if (/^Collector failed safely/i.test(message)) return "Nguồn thu thập dữ liệu gặp sự cố; không có dữ liệu mới được sử dụng.";
  if (/^Deduplicated /i.test(message)) return "Hệ thống đã loại các bằng chứng trùng lặp; các nguồn trùng không được tính là bằng chứng độc lập.";
  if (/^Trend .+ detected\.?$/i.test(message)) return `Đã phát hiện ${message.replace(/^Trend\s+/i, "xu hướng ").replace(/\s+detected\.?$/i, "")}.`;
  if (/^Advertising Angle not found\.?$/i.test(message)) return "Không tìm thấy góc quảng cáo.";
  if (/^Advertising Brief not found\.?$/i.test(message)) return "Không tìm thấy brief quảng cáo.";
  if (/^Campaign( metric snapshot)? not found\.?$/i.test(message)) return "Không tìm thấy chiến dịch hoặc bản ghi số liệu.";
  if (/^Advertising Angle is not eligible/i.test(message)) return "Góc quảng cáo này chưa đủ điều kiện bằng chứng để tạo brief.";
  if (/^Advertising Angle source claim is no longer available/i.test(message)) return "Claim nguồn của góc quảng cáo không còn khả dụng.";
  if (/^Advertising Angle is no longer supported/i.test(message)) return "Góc quảng cáo không còn được đánh giá là đủ điều kiện theo Độ tin cậy sản phẩm hiện tại.";
  if (/^Trend Report source not found/i.test(message)) return "Không tìm thấy báo cáo xu hướng nguồn.";
  if (/^A non-empty, caller-supplied metric payload is required/i.test(message)) return "Hãy nhập ít nhất một chỉ số thực tế để lưu bản ghi.";
  if (/^(captured_at must be timezone-aware|metric_schema is required)/i.test(message)) return "Dữ liệu số liệu chưa hợp lệ. Vui lòng kiểm tra lại thông tin đã nhập.";
  if (ENGLISH_TREND_MESSAGE.test(message)) return "Nguồn dữ liệu xu hướng không trả về thông tin có thể sử dụng. Vui lòng thử lại hoặc kiểm tra cấu hình nguồn.";
  return message;
};

export const presentTrustRationale = (value) => {
  const rationale = String(value || "").trim();
  if (/^conflicting_sources:/i.test(rationale)) return "Có cả bằng chứng ủng hộ và mâu thuẫn; chưa thể xác minh claim này.";
  if (/^explicit suitable evidence contradicts/i.test(rationale)) return "Bằng chứng phù hợp hiện có mâu thuẫn với claim này.";
  if (/^explicit evidence relation supports/i.test(rationale)) return "Bằng chứng liên quan hỗ trợ claim này, nhưng không khẳng định đó là sự thật tuyệt đối về sản phẩm.";
  if (/^user-provided claim has no explicit/i.test(rationale)) return "Claim do người dùng cung cấp chưa có bằng chứng hỗ trợ rõ ràng.";
  if (/^only stale evidence/i.test(rationale)) return "Chỉ có bằng chứng đã cũ liên quan đến claim này.";
  if (/^no explicit relevant evidence/i.test(rationale)) return "Chưa có bằng chứng liên quan rõ ràng cho claim này.";
  return rationale || "Chưa có giải thích bổ sung.";
};
