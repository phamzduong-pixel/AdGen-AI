import { createPortal } from "react-dom";
import { FiX } from "react-icons/fi";

import "./Modal.css";

function Modal({
  open,
  title,
  children,
  footer,
  onClose,
  size = "md",
  closeDisabled = false,
}) {
  if (!open) return null;

  return createPortal(
    <div className="ui-modal" role="dialog" aria-modal="true">
      <button
        type="button"
        className="ui-modal__backdrop"
        onClick={closeDisabled ? undefined : onClose}
        aria-label="Đóng"
      />
      <section className={`ui-modal__panel ui-modal__panel--${size}`}>
        <header>
          <h2>{title}</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={closeDisabled}
            aria-label="Đóng"
          >
            <FiX />
          </button>
        </header>
        <div className="ui-modal__body">{children}</div>
        {footer && <footer>{footer}</footer>}
      </section>
    </div>,
    document.body,
  );
}

export default Modal;
