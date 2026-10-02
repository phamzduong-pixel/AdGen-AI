import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { BsPinAngle, BsPinAngleFill } from "react-icons/bs";
import { FiEdit2, FiTrash2 } from "react-icons/fi";

import "./ConversationMenu.css";

function ConversationMenu({
  anchorRect,
  conversation,
  onClose,
  onRename,
  onDelete,
  onTogglePin,
}) {
  const menuRef = useRef(null);

  useEffect(() => {
    const closeOnOutsideClick = (event) => {
      if (!menuRef.current?.contains(event.target)) onClose();
    };

    const closeOnEscape = (event) => {
      if (event.key === "Escape") onClose();
    };

    const closeOnViewportChange = () => onClose();

    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    window.addEventListener("resize", closeOnViewportChange);
    window.addEventListener("scroll", closeOnViewportChange, true);

    menuRef.current?.querySelector("button")?.focus();

    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
      window.removeEventListener("resize", closeOnViewportChange);
      window.removeEventListener("scroll", closeOnViewportChange, true);
    };
  }, [onClose]);

  if (!anchorRect) return null;

  const menuWidth = 210;
  const menuHeight = 132;
  const left = Math.max(
    8,
    Math.min(anchorRect.right - menuWidth, window.innerWidth - menuWidth - 8),
  );
  const hasSpaceBelow =
    anchorRect.bottom + menuHeight + 8 <= window.innerHeight;
  const top = hasSpaceBelow
    ? anchorRect.bottom + 6
    : Math.max(8, anchorRect.top - menuHeight - 6);

  return createPortal(
    <div
      ref={menuRef}
      className="conversation-menu"
      style={{ left, top }}
      role="menu"
      aria-label={`Tùy chọn cho ${conversation.title}`}
    >
      <button type="button" role="menuitem" onClick={onTogglePin}>
        {conversation.is_pinned ? <BsPinAngleFill /> : <BsPinAngle />}
        {conversation.is_pinned ? "Bỏ ghim" : "Ghim cuộc trò chuyện"}
      </button>

      <button type="button" role="menuitem" onClick={onRename}>
        <FiEdit2 />
        Đổi tên
      </button>

      <button
        type="button"
        role="menuitem"
        className="conversation-menu__danger"
        onClick={onDelete}
      >
        <FiTrash2 />
        Xóa
      </button>
    </div>,
    document.body,
  );
}

export default ConversationMenu;
