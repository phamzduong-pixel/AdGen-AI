import { FiEdit2, FiEye, FiTrash2 } from "react-icons/fi";
import { getPlatformLabel } from "../../../constants/platforms";

const STATUS = {
  draft: "Bản nháp",
  active: "Đang chạy",
  completed: "Hoàn thành",
  archived: "Lưu trữ",
};

function CampaignCard({ campaign, onView, onEdit, onDelete }) {
  const updatedAt = new Date(`${campaign.updated_at}Z`);
  return (
    <article className="campaign-card">
      <header>
        <span className={`campaign-card__status is-${campaign.status}`}>
          {STATUS[campaign.status]}
        </span>
        <small>
          {Number.isNaN(updatedAt.getTime())
            ? ""
            : new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(updatedAt)}
        </small>
      </header>
      <h2>{campaign.name}</h2>
      <p>{campaign.description || "Chưa có mô tả chiến dịch."}</p>
      <dl>
        <div><dt>Sản phẩm</dt><dd>{campaign.product_name || "—"}</dd></div>
        <div><dt>Nền tảng</dt><dd>{getPlatformLabel(campaign.platform, campaign.platform_name) || "Chung"}</dd></div>
        <div><dt>Nội dung</dt><dd>{campaign.contents_count}</dd></div>
      </dl>
      <footer>
        <button type="button" onClick={onView}><FiEye /> Chi tiết</button>
        <button type="button" onClick={onEdit}><FiEdit2 /> Sửa</button>
        <button type="button" className="is-danger" onClick={onDelete}><FiTrash2 /></button>
      </footer>
    </article>
  );
}

export default CampaignCard;
