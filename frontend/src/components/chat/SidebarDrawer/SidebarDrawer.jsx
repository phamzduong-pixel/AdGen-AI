import { useEffect } from "react";
import { FiX } from "react-icons/fi";

import "./SidebarDrawer.css";

function SidebarDrawer({ open, onClose, children }) {
  useEffect(() => {
    if (!open) return undefined;

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose?.();
      }
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="sidebar-drawer"
      role="dialog"
      aria-modal="true"
      aria-label="Menu điều hướng"
    >
      <button
        type="button"
        className="sidebar-drawer__overlay"
        onClick={onClose}
        aria-label="Đóng menu"
      />

      <div className="sidebar-drawer__panel">
        <button
          type="button"
          className="sidebar-drawer__close"
          onClick={onClose}
          aria-label="Đóng menu"
        >
          <FiX />
        </button>

        {children}
      </div>
    </div>
  );
}

export default SidebarDrawer;
