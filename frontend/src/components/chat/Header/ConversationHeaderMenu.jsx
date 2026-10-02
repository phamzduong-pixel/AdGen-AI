import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  FiDownload,
  FiEdit2,
  FiMessageSquare,
  FiTrash2,
} from "react-icons/fi";
import { BsPinAngle, BsPinAngleFill } from "react-icons/bs";

function ConversationHeaderMenu({
  conversation,
  onClose,
  onTogglePin,
  onRename,
  onExport,
  onClearMessages,
  onDelete,
}) {
  const ref = useRef(null);
  const [dialog, setDialog] = useState("");
  const [title, setTitle] = useState(conversation.title);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const close = (event) => {
      if (event.key === "Escape") {
        if (dialog) setDialog("");
        else onClose();
      } else if (!dialog && !ref.current?.contains(event.target)) onClose();
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", close);
    };
  }, [dialog, onClose]);

  const run = async (action) => {
    setLoading(true);
    try { await action(); onClose(); } finally { setLoading(false); }
  };

  return createPortal(
    <>
      <div ref={ref} className="header-popup-menu header-popup-menu--management">
        <button type="button" onClick={() => run(() => onTogglePin(!conversation.is_pinned))}>
          {conversation.is_pinned ? <BsPinAngleFill /> : <BsPinAngle />}
          {conversation.is_pinned ? "Bỏ ghim" : "Ghim cuộc trò chuyện"}
        </button>
        <button type="button" onClick={() => setDialog("rename")}><FiEdit2 />Đổi tên</button>
        <button type="button" onClick={() => { onExport(); onClose(); }}><FiDownload />Xuất cuộc trò chuyện</button>
        <button type="button" onClick={() => setDialog("clear")}><FiMessageSquare />Xóa toàn bộ tin nhắn</button>
        <button type="button" className="header-popup-menu__danger" onClick={() => setDialog("delete")}><FiTrash2 />Xóa cuộc trò chuyện</button>
      </div>

      {dialog && (
        <div className="header-dialog" role="dialog" aria-modal="true">
          <button type="button" className="header-dialog__backdrop" onClick={() => !loading && setDialog("")} aria-label="Đóng" />
          <div className="header-dialog__panel">
            {dialog === "rename" ? (
              <>
                <h2>Đổi tên cuộc trò chuyện</h2>
                <input autoFocus value={title} onChange={(event) => setTitle(event.target.value)} onKeyDown={(event) => {
                  if (event.key === "Enter" && title.trim()) run(() => onRename(title.trim()));
                }} />
              </>
            ) : (
              <>
                <h2>{dialog === "clear" ? "Xóa toàn bộ tin nhắn?" : "Xóa cuộc trò chuyện?"}</h2>
                <p>{dialog === "clear" ? "Mọi tin nhắn và tệp đính kèm sẽ bị xóa, nhưng cuộc trò chuyện vẫn được giữ lại." : "Toàn bộ tin nhắn và tệp đính kèm sẽ bị xóa vĩnh viễn."}</p>
              </>
            )}
            <div className="header-dialog__actions">
              <button type="button" onClick={() => setDialog("")} disabled={loading}>Hủy</button>
              <button type="button" className={dialog === "rename" ? "" : "is-danger"} disabled={loading || (dialog === "rename" && !title.trim())} onClick={() => run(() => dialog === "rename" ? onRename(title.trim()) : dialog === "clear" ? onClearMessages() : onDelete())}>
                {loading ? "Đang xử lý..." : dialog === "rename" ? "Lưu" : "Xóa"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>,
    document.body,
  );
}

export default ConversationHeaderMenu;
