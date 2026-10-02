export const DEFAULT_CONVERSATION_TITLE = "Cuộc trò chuyện mới";

export const getConversationDisplayTitle = (conversation) => {
  const title = conversation?.title?.trim();

  if (!title || title === "New Chat") {
    return DEFAULT_CONVERSATION_TITLE;
  }

  return title;
};
