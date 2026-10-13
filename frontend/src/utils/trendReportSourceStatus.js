const FAILURE_STATUSES = new Set([
  "authentication_error",
  "failed",
  "invalid_request",
  "invalid_response",
  "http_error",
  "network_error",
  "quota_exceeded",
  "timeout",
]);

const normalizeStatus = (value) => String(value || "unknown").trim().toLowerCase();

const RESULT_LABELS = {
  no_valid_entries: { tone: "empty", label: "Nguồn chưa có bài viết hợp lệ" },
  no_topic_matches: { tone: "empty", label: "Có bài viết nhưng không khớp chủ đề" },
  success: { tone: "success", label: "Đã tìm thấy bài phù hợp" },
  timeout: { tone: "failure", label: "Nguồn hết thời gian chờ" },
  invalid_response: { tone: "failure", label: "Không thể đọc dữ liệu nguồn" },
  network_error: { tone: "failure", label: "Không thể kết nối nguồn" },
  unknown: { tone: "neutral", label: "Chưa xác định được nguyên nhân" },
};

const optionalCount = (value) => Number.isInteger(value) && value >= 0 ? value : null;

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
      : { tone: "empty", label: "Chưa có kết quả RSS phù hợp" };
  }
  if (normalized === "empty") {
    return { tone: "empty", label: "Chưa có kết quả RSS phù hợp" };
  }
  if (normalized === "not_configured") {
    return { tone: "empty", label: "Chưa cấu hình" };
  }
  if (normalized === "partial") {
    return isProviderStatus
      ? { tone: "warning", label: count > 0 ? "Có bài từ một phần nguồn" : "Chưa có bài · nguồn gặp lỗi" }
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
    const evidenceCount = optionalCount(item?.evidence_count);
    const presentation = getSourceStatusPresentation({
      status: item?.status,
      evidenceCount: evidenceCount ?? 0,
      isProviderStatus: true,
    });
    const resultState = normalizeStatus(item?.result_state || (item?.status === "empty" ? "unknown" : item?.status));
    const resultPresentation = RESULT_LABELS[resultState] || (item?.status === "empty" ? RESULT_LABELS.unknown : presentation);

    return {
      key: item?.source || item?.platform || String(index),
      source,
      platform,
      status: normalizeStatus(item?.status),
      resultState,
      message: item?.message || "",
      evidenceCount,
      entriesChecked: optionalCount(item?.entries_checked),
      validEntries: optionalCount(item?.valid_entries),
      matchedEntries: optionalCount(item?.matched_entries),
      fromCache: item?.from_cache === true,
      deduplicatedEvidenceIds: Array.isArray(item?.deduplicated_evidence_ids)
        ? item.deduplicated_evidence_ids
        : [],
      ...resultPresentation,
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
