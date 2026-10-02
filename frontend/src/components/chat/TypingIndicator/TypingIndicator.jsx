import "./TypingIndicator.css";

function TypingIndicator() {
  return (
    <div
      className="typing-indicator-row"
      role="status"
      aria-label="AdGen AI đang trả lời"
    >
      <div className="typing-indicator">
        <span className="typing-indicator__dot" />
        <span className="typing-indicator__dot" />
        <span className="typing-indicator__dot" />

        <span className="typing-indicator__text">
          AdGen AI đang tạo nội dung
        </span>
      </div>
    </div>
  );
}

export default TypingIndicator;
