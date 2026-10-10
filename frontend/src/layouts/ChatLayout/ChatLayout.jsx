import { useCallback, useEffect, useRef, useState } from "react";

import "./ChatLayout.css";

const SIDEBAR_MIN_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 480;
const SIDEBAR_DEFAULT_WIDTH = 280;
const SIDEBAR_WIDTH_STORAGE_KEY = "adgen.chat.sidebar.width";

function clampSidebarWidth(width) {
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, width));
}

function ChatLayout({
  sidebar,
  header,
  content,
  footer,
  sidebarCollapsed = false,
}) {
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const storedWidth = Number(window.localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY));
    return Number.isFinite(storedWidth)
      ? clampSidebarWidth(storedWidth)
      : SIDEBAR_DEFAULT_WIDTH;
  });
  const isResizing = useRef(false);

  useEffect(() => {
    window.localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidth));
  }, [sidebarWidth]);

  const stopResizing = useCallback(() => {
    isResizing.current = false;
    document.body.classList.remove("chat-layout--resizing");
  }, []);

  useEffect(() => {
    const handlePointerMove = (event) => {
      if (!isResizing.current) return;
      setSidebarWidth(clampSidebarWidth(event.clientX));
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResizing);
    window.addEventListener("pointercancel", stopResizing);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopResizing);
      window.removeEventListener("pointercancel", stopResizing);
    };
  }, [stopResizing]);

  const startResizing = (event) => {
    if (event.button !== 0) return;
    isResizing.current = true;
    document.body.classList.add("chat-layout--resizing");
    event.preventDefault();
  };

  const handleResizeKeyDown = (event) => {
    const step = event.shiftKey ? 32 : 16;
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setSidebarWidth((width) => clampSidebarWidth(width - step));
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      setSidebarWidth((width) => clampSidebarWidth(width + step));
    } else if (event.key === "Home") {
      event.preventDefault();
      setSidebarWidth(SIDEBAR_MIN_WIDTH);
    } else if (event.key === "End") {
      event.preventDefault();
      setSidebarWidth(SIDEBAR_MAX_WIDTH);
    }
  };

  return (
    <div
      className="chat-layout"
      style={{ "--chat-sidebar-width": `${sidebarCollapsed ? 76 : sidebarWidth}px` }}
    >
      <div className="chat-layout__sidebar">{sidebar}</div>

      {!sidebarCollapsed && (
        <button
          type="button"
          className="chat-layout__resizer"
          aria-label="?i?u ch?nh chi?u r?ng thanh b?n"
          aria-orientation="vertical"
          aria-valuemin={SIDEBAR_MIN_WIDTH}
          aria-valuemax={SIDEBAR_MAX_WIDTH}
          aria-valuenow={sidebarWidth}
          onPointerDown={startResizing}
          onKeyDown={handleResizeKeyDown}
        />
      )}

      <main className="chat-layout__main">
        <div className="chat-layout__header">{header}</div>

        <div className="chat-layout__content">{content}</div>

        <div className="chat-layout__footer">{footer}</div>
      </main>
    </div>
  );
}

export default ChatLayout;
