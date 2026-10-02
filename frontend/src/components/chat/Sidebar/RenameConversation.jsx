import { useEffect, useRef, useState } from "react";

function RenameConversation({ conversation, onSave, onCancel }) {
  const [title, setTitle] = useState(conversation.title || "");
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const save = async () => {
    const normalizedTitle = title.trim().replace(/\s+/g, " ");

    if (!normalizedTitle) {
      setValidationError("Tên cuộc trò chuyện không được để trống.");
      inputRef.current?.focus();
      return;
    }

    if (saving) return;

    setValidationError("");
    setSaving(true);

    try {
      await onSave(normalizedTitle);
    } catch {
      setSaving(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div
      className="conversation-item__rename-wrapper"
      onClick={(event) => event.stopPropagation()}
    >
      <input
        ref={inputRef}
        className="conversation-item__rename"
        value={title}
        disabled={saving}
        aria-label="Tên cuộc trò chuyện"
        aria-invalid={Boolean(validationError)}
        onChange={(event) => {
          setTitle(event.target.value);
          if (validationError) setValidationError("");
        }}
        onKeyDown={(event) => {
          event.stopPropagation();

          if (event.key === "Enter") {
            event.preventDefault();
            save();
          }

          if (event.key === "Escape") {
            event.preventDefault();
            onCancel();
          }
        }}
      />

      {validationError && (
        <span className="conversation-item__rename-error" role="alert">
          {validationError}
        </span>
      )}
    </div>
  );
}

export default RenameConversation;
