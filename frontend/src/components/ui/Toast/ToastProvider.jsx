import { useCallback, useMemo, useState } from "react";

import ToastContext from "./ToastContext";
import ToastContainer from "./ToastContainer";

function getInitialToasts() {
  const authMessage = sessionStorage.getItem("adgen_auth_message");
  sessionStorage.removeItem("adgen_auth_message");
  return authMessage
    ? [{ id: crypto.randomUUID(), type: "warning", message: authMessage }]
    : [];
}

function ToastProvider({ children }) {
  const [toasts, setToasts] = useState(getInitialToasts);

  const closeToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback(
    (message, type = "info", duration = 4000) => {
      if (!message) return;
      const id = crypto.randomUUID();

      setToasts((current) => {
        if (
          current.some(
            (toast) => toast.message === message && toast.type === type,
          )
        ) {
          return current;
        }
        return [...current, { id, type, message }].slice(-4);
      });

      if (duration > 0) {
        window.setTimeout(() => closeToast(id), duration);
      }
    },
    [closeToast],
  );

  const value = useMemo(
    () => ({
      showToast,
      success: (message) => showToast(message, "success"),
      error: (message) => showToast(message, "error", 5500),
      warning: (message) => showToast(message, "warning"),
      info: (message) => showToast(message, "info"),
    }),
    [showToast],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onClose={closeToast} />
    </ToastContext.Provider>
  );
}

export default ToastProvider;
