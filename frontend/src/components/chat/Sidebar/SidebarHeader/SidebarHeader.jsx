import { FiChevronLeft, FiChevronRight, FiEdit3 } from "react-icons/fi";

import "./SidebarHeader.css";

function SidebarHeader({ collapsed = false, onCreateConversation, onToggle }) {
  return (
    <div className="sidebar-header">
      <div className="sidebar-brand-row">
        <div className="sidebar-brand">
          <div className="sidebar-brand__logo">DG</div>

          {!collapsed && (
            <div className="sidebar-brand__content">
              <h1 className="sidebar-brand__title">AdGen AI</h1>

              <p className="sidebar-brand__subtitle">Marketing Assistant</p>
            </div>
          )}
        </div>

        <button
          type="button"
          className="sidebar-collapse-button"
          onClick={onToggle}
          title={collapsed ? "Mở rộng sidebar" : "Thu gọn sidebar"}
        >
          {collapsed ? <FiChevronRight /> : <FiChevronLeft />}
        </button>
      </div>

      <button
        type="button"
        className="sidebar-new-chat"
        onClick={onCreateConversation}
        title="Tạo cuộc trò chuyện mới"
      >
        <FiEdit3 />

        {!collapsed && <span>New Chat</span>}
      </button>
    </div>
  );
}

export default SidebarHeader;
