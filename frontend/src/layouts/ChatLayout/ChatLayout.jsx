import "./ChatLayout.css";

function ChatLayout({ sidebar, header, content, footer }) {
  return (
    <div className="chat-layout">
      <div className="chat-layout__sidebar">{sidebar}</div>

      <main className="chat-layout__main">
        <div className="chat-layout__header">{header}</div>

        <div className="chat-layout__content">{content}</div>

        <div className="chat-layout__footer">{footer}</div>
      </main>
    </div>
  );
}

export default ChatLayout;
