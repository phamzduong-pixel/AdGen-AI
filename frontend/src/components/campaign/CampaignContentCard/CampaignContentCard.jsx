import {
  FiBarChart2,
  FiCheck,
  FiCopy,
  FiDownload,
  FiEye,
  FiRefreshCw,
  FiTrash2,
} from "react-icons/fi";

function CampaignContentCard({
  item,
  pending,
  onView,
  onCopy,
  onEvaluate,
  onVariants,
  onExport,
  onPrimary,
  onRemove,
}) {
  const content = item.saved_content;
  const stats = item.statistics;
  return (
    <article className={`campaign-content-card ${item.is_primary ? "is-primary" : ""}`}>
      <header>
        <div>
          <span>{content.platform || "Nội dung chung"}</span>
          <h3>{content.title}</h3>
        </div>
        {item.is_primary && <strong><FiCheck /> Phiên bản chính</strong>}
      </header>
      <p className="campaign-content-card__excerpt">{content.content}</p>
      <div className="campaign-content-card__stats">
        <span>Đánh giá <strong>{stats.latest_score ?? "—"}</strong></span>
        <span>Sao chép <strong>{stats.copy_count}</strong></span>
        <span>Xuất <strong>{stats.export_count}</strong></span>
        <span>Tạo lại <strong>{stats.regenerate_count}</strong></span>
      </div>
      <footer>
        <button type="button" onClick={onView}><FiEye /> Xem</button>
        <button type="button" onClick={onCopy}><FiCopy /> Sao chép</button>
        <button type="button" onClick={onEvaluate}><FiBarChart2 /> Đánh giá</button>
        <button type="button" onClick={onVariants}><FiRefreshCw /> Tạo bản khác</button>
        <button type="button" onClick={onExport}><FiDownload /> Xuất</button>
        {!item.is_primary && (
          <button type="button" onClick={onPrimary} disabled={pending}>
            <FiCheck /> Chọn bản chính
          </button>
        )}
        <button type="button" className="is-danger" onClick={onRemove} disabled={pending}>
          <FiTrash2 /> Xóa khỏi chiến dịch
        </button>
      </footer>
    </article>
  );
}

export default CampaignContentCard;
