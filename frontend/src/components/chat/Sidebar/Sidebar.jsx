import SidebarHeader from "./SidebarHeader";
import ConversationList from "./ConversationList";
import SidebarFooter from "./SidebarFooter";
import AppNavigation from "../../navigation/AppNavigation";

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
      <SidebarHeader
        collapsed={collapsed}
        onCreateConversation={onCreateConversation}
        onToggle={onToggle}
      />

      <AppNavigation compact={collapsed} />

      <ConversationList
        conversations={conversations}
        selectedConversation={selectedConversation}
        onSelectConversation={onSelectConversation}
        collapsed={collapsed}
        onRenameConversation={onRenameConversation}
        onDeleteConversation={onDeleteConversation}
        onTogglePinConversation={onTogglePinConversation}
      />

      <SidebarFooter collapsed={collapsed} user={user} />
    </aside>
  );
}

export default Sidebar;
