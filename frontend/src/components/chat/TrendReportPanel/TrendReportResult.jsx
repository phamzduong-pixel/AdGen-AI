import { FiExternalLink } from "react-icons/fi";

import { buildSourceStatusCards, getProviderStatusPresentation, getSourceStatusPresentation } from "../../../utils/trendReportSourceStatus";
import { presentTrendMessage } from "../../../utils/trendReportMessage";
import { formatReportDate, reportOverview, safeArticleUrl } from "../../../utils/trendReportView";

function TrendReportResult({ report }) {
  const overview = reportOverview(report);
  const sources = buildSourceStatusCards(report);
  const provider = getProviderStatusPresentation(report);
  const hasArticles = overview.evidences.length > 0;
  const failedSources = sources.filter((source) => !["success", "empty"].includes(source.status));
  let emptyMessage = "Chưa có bài báo được lưu cho truy vấn này. Xem trạng thái từng nguồn để biết lý do.";
  if (!sources.length) {
    emptyMessage = "Chưa có nguồn RSS được cấu hình cho báo cáo này.";
  } else if (failedSources.length === sources.length) {
    emptyMessage = "Chưa thể tìm bài báo vì tất cả nguồn RSS đều gặp lỗi. Bạn có thể tìm lại sau; hệ thống không tự thử lại.";
  } else if (failedSources.length) {
    emptyMessage = "Chưa có bài được lưu từ những nguồn đã đọc được. Một số nguồn gặp lỗi nên kết quả chưa bao quát toàn bộ nguồn RSS.";
  } else if (sources.some((source) => source.status === "success")) {
    emptyMessage = "Nguồn báo có bài khớp, nhưng chưa có bằng chứng hợp lệ được lưu sau bước kiểm tra và loại trùng.";
  } else if (sources.some((source) => source.resultState === "no_topic_matches")) {
    emptyMessage = "Các nguồn đã đọc được bài hợp lệ, nhưng chưa có bài khớp chủ đề này.";
  } else if (sources.every((source) => source.resultState === "no_valid_entries")) {
    emptyMessage = "Các nguồn đã phản hồi nhưng chưa có bài viết hợp lệ để tìm kiếm.";
  }

  return <section className="trend-report-panel__result" aria-label="Kết quả tìm bài báo">
    <header className="trend-report-panel__result-header">
      <div><small>Kết quả cho chủ đề</small><h3>{report.query}</h3></div>
      <span className={`trend-report-panel__result-badge is-${provider.tone}`}>{provider.label}</span>
    </header>
    <p className="trend-report-panel__time">Thu thập báo cáo: {formatReportDate(report.retrieved_at)}</p>
    {!hasArticles ? <div className="trend-report-panel__notice is-warning" role="status"><strong>{emptyMessage}</strong><span>RSS chỉ cung cấp bài trong feed gần đây, không tìm toàn bộ kho bài cũ. Bạn có thể sửa từ khóa ở ô tìm kiếm phía trên.</span></div> : null}
    {hasArticles && report.provider_status === "partial" ? <p className="trend-report-panel__notice is-warning">Chỉ có bài từ những nguồn đã phản hồi; nguồn khác gặp lỗi. Xem trạng thái từng nguồn bên dưới.</p> : null}
    {report.summary ? (hasArticles ? <p className="trend-report-panel__summary">{report.summary}</p> : <details className="trend-report-panel__detail"><summary>Chi tiết phân tích</summary><p className="trend-report-panel__summary">{report.summary}</p></details>) : null}
    <div className="trend-report-panel__metrics" aria-label="Tổng quan kết quả">
      <div><small>Bài phù hợp</small><strong>{overview.articleCount ?? "Chưa có dữ liệu"}</strong></div>
      <div><small>Nhà xuất bản</small><strong>{overview.publisherCount ?? "Chưa có dữ liệu"}</strong></div>
      <div><small>Bài đăng mới nhất</small><strong>{formatReportDate(overview.newestArticleAt)}</strong></div>
    </div>
    {overview.topicClusters.length ? <div className="trend-report-panel__clusters"><strong>Nhóm chủ đề từ bài báo</strong><ul>{overview.topicClusters.map((cluster, index) => <li key={`${cluster.phrase}-${index}`}>{cluster.phrase}{Number.isInteger(cluster.article_count) ? ` · ${cluster.article_count} bài` : ""}</li>)}</ul></div> : null}
    <section className="trend-report-panel__source-statuses" aria-label="Trạng thái nguồn RSS">
      <h4>Trạng thái từng nguồn</h4>
      {sources.length ? <div className="trend-report-panel__status-grid">{sources.map((source) => <article className={`trend-report-panel__status-card is-${source.tone}`} key={source.key}>
        <div className="trend-report-panel__status-card-heading"><strong>{source.source}</strong><span className="trend-report-panel__status-badge">{source.label}</span></div>
        <small>Bằng chứng lưu: {source.evidenceCount ?? "Chưa rõ"}</small>
        {source.entriesChecked !== null ? <small>Đã xét: {source.entriesChecked} · Hợp lệ: {source.validEntries ?? "Chưa rõ"} · Khớp: {source.matchedEntries ?? "Chưa rõ"}</small> : null}
        {source.message ? <p>{presentTrendMessage(source.message)}</p> : null}
        {source.fromCache ? <small>Kết quả dùng lại từ bộ nhớ đệm</small> : null}
      </article>)}</div> : <p className="trend-report-panel__state">Báo cáo này chưa có trạng thái nguồn có cấu trúc.</p>}
    </section>
    {report.caveat ? <details className="trend-report-panel__detail"><summary>Giới hạn và lưu ý nguồn</summary><p className="trend-report-panel__caveat">{presentTrendMessage(report.caveat)}</p></details> : null}
    <section aria-label="Bài báo tìm được"><h4>Bài báo tìm được</h4>
      {overview.evidences.length ? overview.evidences.map((evidence) => {
        const articleUrl = safeArticleUrl(evidence.source_url);
        const verification = getSourceStatusPresentation({ status: evidence.status, evidenceCount: 1 });
        return <article className="trend-report-panel__source" key={evidence.evidence_id}>
          <strong>{evidence.title || "Bài báo chưa có tiêu đề"}</strong>
          <small>{evidence.publisher || "Nguồn chưa rõ"} · <span className={`trend-report-panel__evidence-badge is-${verification.tone}`}>{verification.label}</span></small>
          {evidence.published_at ? <small>Đăng bài: {formatReportDate(evidence.published_at)}</small> : <small>Ngày đăng: Chưa có dữ liệu</small>}
          <small>Thu thập: {formatReportDate(evidence.retrieved_at)}</small>
          {evidence.excerpt ? <p>{evidence.excerpt}</p> : null}
          {articleUrl ? <a href={articleUrl} target="_blank" rel="noopener noreferrer">Đọc bài gốc <FiExternalLink /></a> : null}
        </article>;
      }) : <p className="trend-report-panel__state">Chưa có bài báo để hiển thị trong báo cáo này.</p>}
    </section>
  </section>;
}

export default TrendReportResult;
