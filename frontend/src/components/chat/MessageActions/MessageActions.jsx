import { useCallback, useEffect, useRef, useState } from "react";
import {
  FiBarChart2,
  FiCheck,
  FiBookmark,
  FiCopy,
  FiLoader,
  FiLayers,
  FiMoreHorizontal,
  FiRefreshCw,
  FiShield,
  FiEdit3,
  FiMic,
} from "react-icons/fi";
import { createPortal } from "react-dom";

import "./MessageActions.css";
import useToast from "../../ui/Toast/useToast";

const SECONDARY_ACTIONS = [
  { id: "shorter", label: "Viết ngắn hơn" },
  { id: "longer", label: "Viết dài hơn" },
  { id: "professional", label: "Chuyên nghiệp hơn" },
  { id: "friendly", label: "Thân thiện hơn" },
  { id: "emoji", label: "Thêm hoặc bỏ emoji" },
];

function MessageActions({
  content,
  onAction,
  onToggleSave,
  onEvaluate,
  onGenerateVariants,
  onCopied,
  onCheckBrand,
  onOpenEditor,
  onVoiceover,
  isSaved = false,
  savePending = false,
  disabled = false,
}) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [loadingAction, setLoadingAction] = useState("");
  const menuRef = useRef(null);
  const moreButtonRef = useRef(null);
  const closeMenu = useCallback(() => setMenuOpen(false), []);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const close = (event) => {
      if (
        event.key === "Escape" ||
        (
          !menuRef.current?.contains(event.target) &&
          !moreButtonRef.current?.contains(event.target)
        )
      ) {
        closeMenu();
      }
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", close);
    };
  }, [menuOpen, closeMenu]);

  const copy = async () => {
    if (disabled) return;
    try {
      await navigator.clipboard.writeText(content);
      await onCopied?.();
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      toast.error("Không thể sao chép nội dung. Hãy kiểm tra quyền clipboard.");
    }
  };

  const runAction = async (action) => {
    if (disabled || loadingAction) return;
    closeMenu();
    setLoadingAction(action);
    try {
      if (action === "evaluate") await onEvaluate?.();
      else if (action === "variants") await onGenerateVariants?.();
      else if (action === "brand-check") await onCheckBrand?.();
      else if (action === "editor") await onOpenEditor?.();
      else await onAction?.(action);
    } finally {
      setLoadingAction("");
    }
  };

  const toggleSave = async () => {
    if (disabled || loadingAction || savePending) return;
    setLoadingAction("save");
    try {
      await onToggleSave?.();
    } finally {
      setLoadingAction("");
    }
  };

  const buttonContent = (action, icon, label) =>
    loadingAction === action ? (
      <FiLoader className="message-actions__spinner" />
    ) : (
      <>
        {icon}
        <span>{label}</span>
      </>
    );

  return (
    <div className="message-actions">
      <button type="button" onClick={copy} disabled={disabled}>
        {copied ? <FiCheck /> : <FiCopy />}
        <span>{copied ? "Đã sao chép" : "Sao chép"}</span>
      </button>

      {onOpenEditor && (
        <button
          type="button"
          onClick={() => runAction("editor")}
          disabled={disabled || Boolean(loadingAction)}
        >
          {buttonContent("editor", <FiEdit3 />, "Chỉnh sửa")}
        </button>
      )}

      <button
        type="button"
        onClick={() => runAction("evaluate")}
        disabled={disabled || Boolean(loadingAction)}
      >
        {buttonContent("evaluate", <FiBarChart2 />, "Đánh giá")}
      </button>

      <button
        type="button"
        onClick={() => runAction("variants")}
        disabled={disabled || Boolean(loadingAction)}
      >
        {buttonContent("variants", <FiLayers />, "Tạo A/B")}
      </button>

      {onVoiceover && (
        <button
          type="button"
          onClick={onVoiceover}
          disabled={disabled || Boolean(loadingAction)}
          title="Chuyển kịch bản thành giọng đọc / voiceover"
        >
          <FiMic />
          <span>Voiceover</span>
        </button>
      )}

      {onCheckBrand && (
        <button
          type="button"
          onClick={() => runAction("brand-check")}
          disabled={disabled || Boolean(loadingAction)}
        >
          {buttonContent("brand-check", <FiShield />, "Kiểm tra thương hiệu")}
        </button>
      )}

      <button
        ref={moreButtonRef}
        type="button"
        className={isSaved ? "is-saved" : ""}
        onClick={toggleSave}
        disabled={disabled || Boolean(loadingAction) || savePending}
        title={isSaved ? "Bỏ lưu nội dung" : "Lưu vào thư viện"}
      >
        {buttonContent(
          "save",
          <FiBookmark />,
          isSaved ? "Đã lưu" : "Lưu",
        )}
      </button>

      <button
        type="button"
        onClick={() => runAction("alternative")}
        disabled={disabled || Boolean(loadingAction)}
      >
        {buttonContent("alternative", <FiRefreshCw />, "Phiên bản khác")}
      </button>

      <button
        type="button"
        className="message-actions__more"
        onClick={(event) => {
          event.stopPropagation();
          setMenuOpen((current) => !current);
        }}
        disabled={disabled || Boolean(loadingAction)}
        aria-label="Thêm thao tác"
        aria-expanded={menuOpen}
      >
        <FiMoreHorizontal />
      </button>

      {menuOpen &&
        createPortal(
          <div ref={menuRef} className="message-actions-menu" role="menu">
            {SECONDARY_ACTIONS.map((action) => (
              <button
                type="button"
                role="menuitem"
                key={action.id}
                onClick={() => runAction(action.id)}
              >
                {action.label}
              </button>
            ))}
          </div>,
          document.body,
        )}
    </div>
  );
}

export default MessageActions;
