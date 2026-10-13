export const formatReportDate = (value) => {
  if (!value) return "Chưa có dữ liệu";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? "Chưa có dữ liệu" : parsed.toLocaleString("vi-VN");
};

export const safeArticleUrl = (value) => {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.username || url.password) return null;
    return url.href;
  } catch {
    return null;
  }
};

export const reportOverview = (report) => ({
  articleCount: Number.isInteger(report?.article_count) && report.article_count >= 0 ? report.article_count : null,
  publisherCount: Number.isInteger(report?.publisher_count) && report.publisher_count >= 0 ? report.publisher_count : null,
  newestArticleAt: report?.newest_article_at || null,
  topicClusters: Array.isArray(report?.topic_clusters) ? report.topic_clusters : [],
  evidences: Array.isArray(report?.evidences) ? report.evidences : [],
});

export const requestTopicSearch = (retrieve, query, conversationId) => retrieve({
  query,
  conversation_id: conversationId ? Number(conversationId) : undefined,
});

export const requestReportHistory = (listReports) => listReports();
