import { useMemo, useState } from "react";

import ConversationItem from "../ConversationItem.jsx";
import ConversationSearch from "../ConversationSearch";
import "./ConversationList.css";

function ConversationList({
  conversations = [],
  selectedConversation,
  onSelectConversation,
  collapsed = false,
  onRenameConversation,
  onDeleteConversation,
  onTogglePinConversation,
}) {
  const [search, setSearch] = useState("");
  const filteredConversations = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("vi");
    if (!query) return conversations;
    return conversations.filter((conversation) =>
      conversation.title?.toLocaleLowerCase("vi").includes(query),
    );
  }, [conversations, search]);

  return (
    <div className="conversation-list">
      {!collapsed && (
        <>
          <div className="conversation-list__header">
            <span>Cuộc trò chuyện</span>
          </div>
          <ConversationSearch value={search} onChange={setSearch} />
        </>
      )}

      <div className="conversation-list__items">
        {filteredConversations.length === 0
          ? !collapsed && (
              <div className="conversation-list__empty">
                <p>
                  {search
                    ? "Không tìm thấy cuộc trò chuyện"
                    : "Chưa có cuộc trò chuyện"}
                </p>
                {!search && (
                  <span>Hãy tạo một cuộc trò chuyện mới để bắt đầu.</span>
                )}
              </div>
            )
          : filteredConversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                isSelected={conversation.id === selectedConversation}
                onSelect={onSelectConversation}
                collapsed={collapsed}
                onRename={onRenameConversation}
                onDelete={onDeleteConversation}
                onTogglePin={onTogglePinConversation}
              />
            ))}
      </div>
    </div>
  );
}

export default ConversationList;
