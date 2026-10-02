import { FiArrowLeft, FiCloud, FiCloudOff, FiLoader } from "react-icons/fi";
import { getPlatformLabel } from "../../../constants/platforms";
import "./ContentEditorHeader.css";

const STATUS_LABELS = {
  saving: "Đang lưu...",
  saved: "Đã lưu",
  unsaved: "Chưa lưu",
  error: "Chưa thể lưu",
  idle: "",
};

function ContentEditorHeader({
  document,
  draft,
  saveStatus,
  onClose,
}) {
  const StatusIcon =
    saveStatus === "saving"
      ? FiLoader
      : saveStatus === "error"
        ? FiCloudOff
        : FiCloud;

  return (
    <header className="content-editor-header">
      <button type="button" onClick={onClose} aria-label="Đóng trình soạn thảo">
        <FiArrowLeft />
      </button>
      <div className="content-editor-header__identity">
        <span>Trình soạn thảo nội dung</span>
        <strong>{draft.title || "Nội dung chưa đặt tên"}</strong>
      </div>
      <div className="content-editor-header__meta">
        {document?.platform && <span>{getPlatformLabel(document.platform, document.platform_name)}</span>}
        {document?.brand_name && <span>{document.brand_name}</span>}
        {document?.campaign_name && <span>{document.campaign_name}</span>}
      </div>
      <div className={`content-editor-header__status is-${saveStatus}`}>
        <StatusIcon className={saveStatus === "saving" ? "is-spinning" : ""} />
        <span>{STATUS_LABELS[saveStatus]}</span>
      </div>
    </header>
  );
}

export default ContentEditorHeader;
