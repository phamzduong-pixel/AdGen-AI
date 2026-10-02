import {
  FiAlertCircle,
  FiAlertTriangle,
  FiCheckCircle,
  FiInfo,
  FiX,
} from "react-icons/fi";

import "./Toast.css";

const ICONS = {
  success: FiCheckCircle,
  error: FiAlertCircle,
  warning: FiAlertTriangle,
  info: FiInfo,
};

function ToastContainer({ toasts, onClose }) {
  return (
    <div className="toast-container" aria-live="polite" aria-atomic="false">
      {toasts.map((toast) => {
        const Icon = ICONS[toast.type] || FiInfo;
        return (
          <div className={`toast toast--${toast.type}`} role="status" key={toast.id}>
            <Icon className="toast__icon" />
            <span>{toast.message}</span>
            <button type="button" onClick={() => onClose(toast.id)} aria-label="Đóng thông báo">
              <FiX />
            </button>
          </div>
        );
      })}
    </div>
  );
}

export default ToastContainer;
