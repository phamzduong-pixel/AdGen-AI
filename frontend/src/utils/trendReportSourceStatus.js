const FAILURE_STATUSES = new Set([
  "authentication_error",
  "invalid_request",
  "invalid_response",
  "http_error",
  "network_error",
  "quota_exceeded",
  "timeout",
]);

const normalizeStatus = (value) => String(value || "unknown").trim().toLowerCase();

export const getSourceStatusPresentation = ({ status, evidenceCount = 0, isProviderStatus = false } = {}) => {
  const normalized = normalizeStatus(status);
  const count = Number.isFinite(Number(evidenceCount)) ? Number(evidenceCount) : 0;

  if (normalized === "stale") {
    return { tone: "stale", label: "Dữ liệu đã cũ" };
  }
  if (normalized === "conflicting") {
    return { tone: "conflicting", label: "Bằng chứng mâu thuẫn" };
  }
  if (normalized === "success") {
    return count > 0
      ? { tone: "success", label: "Thành công" }
      : { tone: "empty", label: "Không có bằng chứng" };
  }
  if (normalized === "empty") {
    return { tone: "empty", label: "Không có bằng chứng" };
  }
  if (normalized === "not_configured") {
    return { tone: "empty", label: "Chưa cấu hình" };
  }
  if (normalized === "partial") {
    return isProviderStatus
      ? { tone: "failure", label: "Một phần / nguồn gặp lỗi" }
      : { tone: "warning", label: "Bằng chứng một phần" };
  }
  if (FAILURE_STATUSES.has(normalized)) {
    return { tone: "failure", label: "Nguồn gặp lỗi" };
  }
  if (normalized === "verified") {
    return { tone: "success", label: "Đã xác minh" };
  }
  if (normalized === "partial_evidence") {
    return { tone: "warning", label: "Bằng chứng một phần" };
  }
  if (normalized === "unverified") {
    return { tone: "neutral", label: "Chưa xác minh" };
  }
  return { tone: "neutral", label: "Chưa có trạng thái" };
};

export const buildSourceStatusCards = (report) => {
  const sourceStatuses = Array.isArray(report?.source_statuses)
    ? report.source_statuses
    : [];

  return sourceStatuses.map((item, index) => {
    const source = item?.source || item?.platform || "Nguồn không xác định";
    const platform = item?.platform || item?.source || "Nền tảng không xác định";
    const evidenceCount = Number.isFinite(Number(item?.evidence_count))
      ? Number(item.evidence_count)
      : 0;
    const presentation = getSourceStatusPresentation({
      status: item?.status,
      evidenceCount,
      isProviderStatus: true,
    });

    return {
      key: item?.source || item?.platform || String(index),
      source,
      platform,
      status: normalizeStatus(item?.status),
      message: item?.message || "",
      evidenceCount,
      fromCache: item?.from_cache === true,
      deduplicatedEvidenceIds: Array.isArray(item?.deduplicated_evidence_ids)
        ? item.deduplicated_evidence_ids
        : [],
      ...presentation,
    };
  });
};

export const getProviderStatusPresentation = (report) => (
  getSourceStatusPresentation({
    status: report?.provider_status,
    evidenceCount: Array.isArray(report?.evidences) ? report.evidences.length : 0,
    isProviderStatus: true,
  })
);
