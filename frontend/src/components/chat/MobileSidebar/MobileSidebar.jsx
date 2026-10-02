import Sidebar from "../Sidebar";
import SidebarDrawer from "../SidebarDrawer";

import "./MobileSidebar.css";

function MobileSidebar({
  open,
  onClose,
  conversations = [],
  selectedConversation,
  onCreateConversation,
  onSelectConversation,
  user,
  onRenameConversation,
  onDeleteConversation,
  onTogglePinConversation,
}) {
  return (
    <SidebarDrawer open={open} onClose={onClose}>
      <div className="mobile-sidebar">
        <Sidebar
          conversations={conversations}
          selectedConversation={selectedConversation}
          onCreateConversation={onCreateConversation}
          onSelectConversation={onSelectConversation}
          collapsed={false}
          user={user}
          onRenameConversation={onRenameConversation}
          onDeleteConversation={onDeleteConversation}
          onTogglePinConversation={onTogglePinConversation}
        />
      </div>
    </SidebarDrawer>
  );
}

export default MobileSidebar;
