export const actionPresentation = (action) => ({
  allow: { label: "Có thể sử dụng", canCreate: true, tone: "allow" },
  soften: { label: "Nên diễn đạt thận trọng", canCreate: true, tone: "soften" },
  ask_user: { label: "Cần xác nhận thêm", canCreate: false, tone: "ask" },
  block: { label: "Không nên sử dụng", canCreate: false, tone: "block" },
}[String(action || "").toLowerCase()] || { label: "Chưa thể sử dụng", canCreate: false, tone: "ask" });

export const metricEntries = (payload) => (
  payload && typeof payload === "object" && !Array.isArray(payload)
    ? Object.entries(payload)
    : []
);

export const snapshotTone = (status) => ({ success: "success", empty: "empty", error: "error" }[String(status || "").toLowerCase()] || "empty");
