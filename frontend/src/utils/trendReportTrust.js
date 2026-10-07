const labels = {
  evidence_supported: "Bằng chứng đã xác minh",
  partial: "Bằng chứng một phần",
  unverified: "Chưa xác minh",
  contradicted: "Mâu thuẫn",
  insufficient_evidence: "Thiếu bằng chứng",
  verified: "Đã xác minh",
  insufficient: "Thiếu bằng chứng",
};

const actionLabels = {
  allow: "Có thể sử dụng",
  soften: "Nên diễn đạt thận trọng",
  ask_user: "Cần làm rõ thêm",
  block: "Không được sử dụng",
};

export const trustPresentation = (claim = {}) => {
  const status = String(claim.status || "unverified").toLowerCase();
  const action = String(claim.recommended_action || "soften").toLowerCase();
  const highRisk = String(claim.risk_level || "normal").toLowerCase() === "high";
  const tone = action === "block" || (highRisk && status === "contradicted")
    ? "block" : action === "ask_user" || action === "soften" || status !== "evidence_supported"
      ? "caution" : "info";
  return { status, action, highRisk, tone, label: labels[status] || "Chưa có trạng thái", actionLabel: actionLabels[action] || "Cần xem xét" };
};

export const trustWarning = (trust = {}) => {
  if (Array.isArray(trust.blocking_claim_ids) && trust.blocking_claim_ids.length) {
    return { tone: "block", text: "Không thể tạo nội dung: claim rủi ro cao mâu thuẫn với bằng chứng hiện có." };
  }
  if (trust.requires_review) return { tone: "caution", text: "Một số claim cần được xem xét; bằng chứng và chính sách nguồn vẫn là căn cứ quyết định." };
  return { tone: "info", text: "Các claim dưới đây dựa trên phạm vi bằng chứng, không phải độ tự tin của AI." };
};
