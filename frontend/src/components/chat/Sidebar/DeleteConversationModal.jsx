import { useEffect } from "react";
import { createPortal } from "react-dom";
import { FiAlertTriangle } from "react-icons/fi";

import Button from "../../ui/Button/Button";
import "./DeleteConversationModal.css";

function DeleteConversationModal({
  conversation,
  deleting,
  onCancel,
  onConfirm,
}) {
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !deleting) onCancel();
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [deleting, onCancel]);

  return createPortal(
    <div
      className="delete-conversation-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-conversation-title"
    >
      <button
        type="button"
        className="delete-conversation-modal__backdrop"
        aria-label="Đóng"
        onClick={onCancel}
        disabled={deleting}
      />

      <div className="delete-conversation-modal__panel">
        <span className="delete-conversation-modal__icon">
          <FiAlertTriangle />
        </span>

        <div className="delete-conversation-modal__content">
          <h2 id="delete-conversation-title">Xóa cuộc trò chuyện?</h2>
          <p>
            “{conversation.title}” và toàn bộ lịch sử tin nhắn bên trong sẽ bị
            xóa vĩnh viễn. Hành động này không thể hoàn tác.
          </p>
        </div>

        <div className="delete-conversation-modal__actions">
          <Button variant="secondary" onClick={onCancel} disabled={deleting}>
            Hủy
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={deleting}>
            Xóa
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export default DeleteConversationModal;
