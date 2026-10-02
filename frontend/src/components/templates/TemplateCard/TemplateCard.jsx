import {
  FiCopy,
  FiEdit2,
  FiHeart,
  FiMail,
  FiMessageCircle,
  FiMonitor,
  FiSearch,
  FiShoppingBag,
  FiTrash2,
  FiVideo,
} from "react-icons/fi";

import { getPlatformLabel } from "../../../constants/platforms";
import "./TemplateCard.css";

const PLATFORM_META = {
  facebook: ["Facebook", FiMessageCircle],
  google_ads: ["Google Ads", FiSearch],
  instagram: ["Instagram", FiMessageCircle],
  tiktok: ["TikTok", FiVideo],
  landing_page: ["Landing Page", FiMonitor],
  email: ["Email", FiMail],
  shopee: ["Shopee", FiShoppingBag],
  other: ["Khác", FiMonitor],
};

function TemplateCard({
  template,
  pending,
  onUse,
  onFavorite,
  onEdit,
  onDelete,
  onClone,
  compact = false,
}) {
  const [platformLabel, PlatformIcon] =
    PLATFORM_META[template.platform] || [getPlatformLabel(template.platform, template.platform_name), FiMonitor];
  const displayPlatformLabel = getPlatformLabel(template.platform, template.platform_name) || platformLabel;

  return (
    <article
      className={`template-card ${compact ? "template-card--compact" : ""}`}
    >
      <div className="template-card__top">
        <span className={`template-card__platform is-${template.platform}`}>
          <PlatformIcon />
          {displayPlatformLabel}
        </span>
        <button
          type="button"
          className={`template-card__favorite ${
            template.is_favorite ? "is-active" : ""
          }`}
          onClick={() => onFavorite?.(template)}
          disabled={pending}
          aria-label={
            template.is_favorite
              ? "Bỏ khỏi mẫu yêu thích"
              : "Thêm vào mẫu yêu thích"
          }
          title={
            template.is_favorite
              ? "Bỏ khỏi yêu thích"
              : "Thêm vào yêu thích"
          }
        >
          <FiHeart />
        </button>
      </div>

      <div className="template-card__body">
        <span className="template-card__category">{template.category}</span>
        <h3>{template.title}</h3>
        <p>{template.description}</p>
        <div className="template-card__meta">
          <span>{template.default_tone}</span>
          <span>{template.default_length}</span>
          {!template.is_system && <span>Mẫu cá nhân</span>}
        </div>
      </div>

      <div className="template-card__actions">
        <button
          type="button"
          className="template-card__use"
          onClick={() => onUse?.(template)}
          disabled={pending}
        >
          Sử dụng mẫu
        </button>
        {template.is_system && onClone && (
          <button
            type="button"
            className="template-card__icon-action"
            onClick={() => onClone(template)}
            disabled={pending}
            title="Nhân bản thành mẫu cá nhân"
            aria-label="Nhân bản thành mẫu cá nhân"
          >
            <FiCopy />
          </button>
        )}
        {template.is_owner && (
          <>
            <button
              type="button"
              className="template-card__icon-action"
              onClick={() => onEdit?.(template)}
              disabled={pending}
              title="Chỉnh sửa mẫu"
              aria-label="Chỉnh sửa mẫu"
            >
              <FiEdit2 />
            </button>
            <button
              type="button"
              className="template-card__icon-action is-danger"
              onClick={() => onDelete?.(template)}
              disabled={pending}
              title="Xóa mẫu"
              aria-label="Xóa mẫu"
            >
              <FiTrash2 />
            </button>
          </>
        )}
      </div>
    </article>
  );
}

export default TemplateCard;
