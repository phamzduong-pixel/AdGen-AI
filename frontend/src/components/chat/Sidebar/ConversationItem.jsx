import { useCallback, useRef, useState } from "react";
import { BsPinAngleFill } from "react-icons/bs";
import { FiMessageSquare, FiMoreHorizontal } from "react-icons/fi";

import ConversationMenu from "./ConversationMenu";
import DeleteConversationModal from "./DeleteConversationModal";
import RenameConversation from "./RenameConversation";
import { getConversationDisplayTitle } from "../../../utils/conversationTitle";
import { getPreferences } from "../../../utils/settingsStorage";
import "./ConversationItem.css";

function ConversationItem({
  conversation,
  isSelected = false,
  onSelect,
  onRename,
  onDelete,
  onTogglePin,
  collapsed = false,
}) {
  const [menuRect, setMenuRect] = useState(null);
  const [renaming, setRenaming] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [actionPending, setActionPending] = useState(false);
  const moreButtonRef = useRef(null);

  const title = getConversationDisplayTitle(conversation);
  const closeMenu = useCallback(() => setMenuRect(null), []);

  const toggleMenu = (event) => {
    event.preventDefault();
    event.stopPropagation();

    setMenuRect((currentRect) =>
      currentRect ? null : moreButtonRef.current?.getBoundingClientRect(),
    );
  };

  const handleTogglePin = async () => {
    if (actionPending || typeof onTogglePin !== "function") return;

    closeMenu();
    setActionPending(true);

    try {
      await onTogglePin(conversation.id, !conversation.is_pinned);
    } finally {
      setActionPending(false);
    }
  };

  const handleDelete = async () => {
    if (deleting || typeof onDelete !== "function") return;

    setDeleting(true);

    try {
      await onDelete(conversation.id);
      setConfirmingDelete(false);
    } catch {
      setDeleting(false);
    }
  };

  return (
    <>
      <div
        className={`conversation-item ${
          isSelected ? "conversation-item--selected" : ""
        } ${collapsed ? "conversation-item--collapsed" : ""} ${
          menuRect ? "conversation-item--menu-open" : ""
        }`}
        role="button"
        tabIndex={0}
        title={collapsed ? title : undefined}
        onClick={() => {
          if (!renaming) onSelect?.(conversation.id);
        }}
        onKeyDown={(event) => {
          if (
            !renaming &&
            (event.key === "Enter" || event.key === " ")
          ) {
            event.preventDefault();
            onSelect?.(conversation.id);
          }
        }}
      >
        <span className="conversation-item__icon">
          <FiMessageSquare />
        </span>

        {!collapsed && (
          <>
            {renaming ? (
              <RenameConversation
                conversation={conversation}
                onCancel={() => setRenaming(false)}
                onSave={async (newTitle) => {
                  if (typeof onRename !== "function") return;
                  await onRename(conversation.id, newTitle);
                  setRenaming(false);
                }}
              />
            ) : (
              <span className="conversation-item__title">{title}</span>
            )}

            {conversation.is_pinned && !renaming && (
              <BsPinAngleFill
                className="conversation-item__pin"
                aria-label="Đã ghim"
              />
            )}

            {!renaming && (
              <button
                ref={moreButtonRef}
                type="button"
                className="conversation-item__more-button"
                onClick={toggleMenu}
                aria-label={`Tùy chọn cho ${title}`}
                aria-haspopup="menu"
                aria-expanded={Boolean(menuRect)}
              >
                <FiMoreHorizontal />
              </button>
            )}
          </>
        )}
      </div>

      {menuRect && (
        <ConversationMenu
          anchorRect={menuRect}
          conversation={conversation}
          onClose={closeMenu}
          onRename={() => {
            closeMenu();
            setRenaming(true);
          }}
          onDelete={() => {
            closeMenu();
            if (getPreferences().confirmBeforeDelete) {
              setConfirmingDelete(true);
            } else {
              handleDelete();
            }
          }}
          onTogglePin={handleTogglePin}
        />
      )}

      {confirmingDelete && (
        <DeleteConversationModal
          conversation={conversation}
          deleting={deleting}
          onCancel={() => {
            if (!deleting) setConfirmingDelete(false);
          }}
          onConfirm={handleDelete}
        />
      )}
    </>
  );
}

export default ConversationItem;
