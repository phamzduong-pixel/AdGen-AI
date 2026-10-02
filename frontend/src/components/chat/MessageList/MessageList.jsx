import { useEffect, useRef } from "react";
import "./MessageList.css";

function MessageList({
  children,
  isLoading = false,
  autoScroll = true,
  scrollTrigger,
  isEmpty = false,
}) {
  const containerRef = useRef(null);
  const bottomRef = useRef(null);

  const scrollToBottom = (behavior = "smooth") => {
    const container = containerRef.current;
    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior,
      });
    } else {
      bottomRef.current?.scrollIntoView({
        behavior,
        block: "end",
      });
    }
  };

  useEffect(() => {
    if (!autoScroll || isLoading) return;

    // Scroll to bottom without scrolling entire window/ancestors
    requestAnimationFrame(() => {
      scrollToBottom("smooth");
    });
  }, [scrollTrigger, autoScroll, isLoading]);

  return (
    <section
      ref={containerRef}
      className={`message-list${isEmpty ? " message-list--empty" : ""}`}
    >
      <div className="message-list__inner">
        {isLoading ? (
          <div className="message-list__loading">
            Đang tải cuộc trò chuyện...
          </div>
        ) : (
          children
        )}

        <div ref={bottomRef} style={{ height: "1px", width: "100%", pointerEvents: "none" }} />
      </div>
    </section>
  );
}

export default MessageList;