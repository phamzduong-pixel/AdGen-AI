import "./ConversationItem.css";

function ConversationItem({ conversation, isSelected, onSelect }) {
  return (
    <button
      type="button"
      className={`conversation-item ${
        isSelected ? "conversation-item--selected" : ""
      }`}
      onClick={() => onSelect?.(conversation.id)}
    >
      <span className="conversation-item__icon">💬</span>

      <span className="conversation-item__title">
        {conversation.title || "New Chat"}
      </span>
    </button>
  );
}

export default ConversationItem;
