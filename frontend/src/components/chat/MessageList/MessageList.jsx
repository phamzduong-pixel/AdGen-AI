import { useEffect, useRef } from "react";
import { isNearBottom } from "../../../utils/messageListScroll.js";
import "./MessageList.css";

function MessageList({
  children,
  isLoading = false,
  autoScroll = true,
  scrollContext,
  scrollTrigger,
  isEmpty = false,
}) {
  const containerRef = useRef(null);
  const shouldFollowRef = useRef(true);
  const scrollContextRef = useRef(scrollContext);

  const scrollToBottom = () => {
    const container = containerRef.current;
    if (container) container.scrollTop = container.scrollHeight;
  };

  useEffect(() => {
    if (scrollContextRef.current === scrollContext) return;

    scrollContextRef.current = scrollContext;
    shouldFollowRef.current = true;
  }, [scrollContext]);

  useEffect(() => {
    if (!autoScroll || isLoading || !shouldFollowRef.current) return;

    const frame = requestAnimationFrame(() => {
      if (autoScroll && !isLoading && shouldFollowRef.current) {
        scrollToBottom();
      }
    });

    return () => cancelAnimationFrame(frame);
  }, [scrollTrigger, autoScroll, isLoading]);

  const handleScroll = () => {
    shouldFollowRef.current = isNearBottom(containerRef.current);
  };

  return (
    <section
      ref={containerRef}
      className={`message-list${isEmpty ? " message-list--empty" : ""}`}
      onScroll={handleScroll}
    >
      <div className="message-list__inner">
        {isLoading ? (
          <div className="message-list__loading">
            Đang tải cuộc trò chuyện...
          </div>
        ) : (
          children
        )}

      </div>
    </section>
  );
}

export default MessageList;
