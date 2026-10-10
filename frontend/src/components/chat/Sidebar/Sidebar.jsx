import SidebarHeader from "./SidebarHeader";
import ConversationList from "./ConversationList";
import SidebarFooter from "./SidebarFooter";
import AppNavigation, { NAVIGATION_ITEMS } from "../../navigation/AppNavigation";

import "./Sidebar.css";

function Sidebar({
  conversations = [],
  selectedConversation,
  onCreateConversation,
  onSelectConversation,
  collapsed = false,
  onToggle,
  user = null,
  onRenameConversation,
  onDeleteConversation,
  onTogglePinConversation,
}) {
  return (
    <aside className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
      <div className="sidebar__fixed">
        <SidebarHeader
          collapsed={collapsed}
          onCreateConversation={onCreateConversation}
          onToggle={onToggle}
        />
        <AppNavigation compact={collapsed} items={NAVIGATION_ITEMS.slice(0, 2)} />
      </div>

      <div className="sidebar__scrollable">
        <AppNavigation compact={collapsed} items={NAVIGATION_ITEMS.slice(2)} />
        <ConversationList
          conversations={conversations}
          selectedConversation={selectedConversation}
          onSelectConversation={onSelectConversation}
          collapsed={collapsed}
          onRenameConversation={onRenameConversation}
          onDeleteConversation={onDeleteConversation}
          onTogglePinConversation={onTogglePinConversation}
        />
      </div>

      <SidebarFooter collapsed={collapsed} user={user} />
    </aside>
  );
}

export default Sidebar;
