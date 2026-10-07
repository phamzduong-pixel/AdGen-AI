import HeaderTitle from "./HeaderTitle";
import HeaderActions from "./HeaderActions";
import HamburgerButton from "../HamburgerButton";

import "./Header.css";

function Header({
  title = "Cuộc trò chuyện mới",
  onCreateConversation,
  onOpenMobileSidebar,
  onExport,
  exportDisabled = false,
  onOpenConversationMenu,
  onOpenSavedContents,
  onOpenTrendReports,
  onOpenMedia,
}) {
  return (
    <header className="chat-header">
      <div className="chat-header__left">
        <HamburgerButton onClick={onOpenMobileSidebar} />

        <HeaderTitle title={title} />
      </div>

      <HeaderActions
        onCreateConversation={onCreateConversation}
        onExport={onExport}
        exportDisabled={exportDisabled}
        onOpenConversationMenu={onOpenConversationMenu}
        onOpenSavedContents={onOpenSavedContents}
        onOpenTrendReports={onOpenTrendReports}
        onOpenMedia={onOpenMedia}
      />
    </header>
  );
}

export default Header;