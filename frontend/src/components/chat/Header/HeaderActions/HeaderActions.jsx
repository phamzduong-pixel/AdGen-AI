import { useCallback, useRef, useState } from "react";
import {
  FiBookmark,
  FiDownload,
  FiImage,
  FiEdit3,
  FiMoreHorizontal,
} from "react-icons/fi";

import ExportMenu from "../ExportMenu";
import "./HeaderActions.css";

function HeaderActions({
  onCreateConversation,
  onExport,
  exportDisabled,
  onOpenConversationMenu,
  onOpenSavedContents,
  onOpenMedia,
}) {
  const [exportOpen, setExportOpen] = useState(false);
  const exportButtonRef = useRef(null);
  const closeExport = useCallback(() => setExportOpen(false), []);

  return (
    <div className="header-actions">
      <button
        type="button"
        className="header-actions__button"
        onClick={onOpenSavedContents}
        title="Thư viện nội dung"
      >
        <FiBookmark />
        <span>Thư viện</span>
      </button>

      <button
        type="button"
        className="header-actions__button"
        onClick={onOpenMedia}
        title="Tạo và chỉnh sửa ảnh"
      >
        <FiImage />
        <span>Media</span>
      </button>

      <button
        ref={exportButtonRef}
        type="button"
        className="header-actions__button"
        onClick={(event) => {
          event.stopPropagation();
          setExportOpen((current) => !current);
        }}
        disabled={exportDisabled}
        title="Xuất nội dung"
      >
        <FiDownload />
        <span>Xuất</span>
      </button>

      <button
        type="button"
        className="header-actions__button header-actions__button--primary"
        onClick={onCreateConversation}
        title="Tạo cuộc trò chuyện mới"
      >
        <FiEdit3 />
        <span>Cuộc trò chuyện mới</span>
      </button>

      <button
        type="button"
        className="header-actions__icon-button"
        title="Quản lý cuộc trò chuyện"
        aria-label="Quản lý cuộc trò chuyện"
        onClick={onOpenConversationMenu}
      >
        <FiMoreHorizontal />
      </button>

      {exportOpen && (
        <ExportMenu
          disabled={exportDisabled}
          onExport={onExport}
          onClose={closeExport}
        />
      )}
    </div>
  );
}

export default HeaderActions;
