import { useEffect, useRef, useState } from "react";
import { FiFile, FiFileText, FiLoader } from "react-icons/fi";
import { createPortal } from "react-dom";

function ExportMenu({ disabled, onExport, onClose }) {
  const ref = useRef(null);
  const [loading, setLoading] = useState("");

  useEffect(() => {
    const close = (event) => {
      if (event.key === "Escape" || !ref.current?.contains(event.target)) onClose();
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", close);
    };
  }, [onClose]);

  const run = async (format) => {
    setLoading(format);
    try { await onExport(format); onClose(); } finally { setLoading(""); }
  };

  return createPortal(
    <div ref={ref} className="header-popup-menu">
      <button type="button" disabled={disabled || loading} onClick={() => run("pdf")}><FiFile />Xuất PDF{loading === "pdf" && <FiLoader />}</button>
      <button type="button" disabled={disabled || loading} onClick={() => run("markdown")}><FiFileText />Xuất Markdown</button>
      <button type="button" disabled={disabled || loading} onClick={() => run("txt")}><FiFileText />Xuất TXT</button>
    </div>,
    document.body,
  );
}

export default ExportMenu;
