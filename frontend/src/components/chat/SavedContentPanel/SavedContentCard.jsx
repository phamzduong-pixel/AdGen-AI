import {
  FiBookmark,
  FiCopy,
  FiEye,
  FiLoader,
  FiTrash2,
  FiEdit3,
} from "react-icons/fi";
import { getPlatformLabel } from "../../../constants/platforms";

const PLATFORM_LABELS = {
  shopee: "Shopee",
  other: "Khác",
  facebook: "Facebook",
  google_ads: "Google Ads",
  landing_page: "Landing Page",
  instagram: "Instagram",
  tiktok: "TikTok",
  email: "Email Marketing",
};

function SavedContentCard({
  item,
  deleting = false,
  onView,
  onCopy,
  onDelete,
  onEdit,
}) {
  const createdAt = new Date(
    typeof item.created_at === "string" &&
      !item.created_at.endsWith("Z") &&
      !item.created_at.includes("+")
      ? `${item.created_at}Z`
      : item.created_at,
  );
  const savedDate = Number.isNaN(createdAt.getTime())
    ? ""
    : new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Asia/Ho_Chi_Minh",
      }).format(createdAt);

  return (
    <article className="saved-content-card">
      <div className="saved-content-card__heading">
        <span className="saved-content-card__icon">
          <FiBookmark />
        </span>
        <div>
          <h3>{item.title}</h3>
          <p>
            {getPlatformLabel(item.platform, item.platform_name) || PLATFORM_LABELS[item.platform] || "Nội dung chung"}
            {savedDate && <span> · {savedDate}</span>}
            {item.brand_name && <span> · {item.brand_name}</span>}
          </p>
        </div>
      </div>

      <p className="saved-content-card__excerpt">{item.content}</p>

      <div className="saved-content-card__actions">
        {onEdit && (
          <button type="button" onClick={() => onEdit(item)}>
            <FiEdit3 />
            Chỉnh sửa
          </button>
        )}
        <button type="button" onClick={() => onView(item)}>
          <FiEye />
          Xem chi tiết
        </button>
        <button type="button" onClick={() => onCopy(item)}>
          <FiCopy />
          Sao chép
        </button>
        <button
          type="button"
          className="is-danger"
          onClick={() => onDelete(item)}
          disabled={deleting}
        >
          {deleting ? <FiLoader className="saved-content-card__spinner" /> : <FiTrash2 />}
          Bỏ lưu
        </button>
      </div>
    </article>
  );
}

export default SavedContentCard;
