import { useCallback, useEffect, useState } from "react";

import {
  createConversation,
  getConversations,
} from "../services/api/conversationApi";

function useConversation() {
  const [conversations, setConversations] = useState([]);

  const [selectedConversation, setSelectedConversation] = useState(null);

  const loadConversations = useCallback(async () => {
    try {
      const data = await getConversations();

      setConversations(data);

      if (data.length) {
        setSelectedConversation(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    // Initial remote data synchronization is intentionally performed on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadConversations();
  }, [loadConversations]);

  const handleCreateConversation = async () => {
    const conversation = await createConversation();

    setConversations((prev) => [conversation, ...prev]);

    setSelectedConversation(conversation.id);
  };

  return {
    conversations,
    selectedConversation,
    setSelectedConversation,
    handleCreateConversation,
    refreshConversations: loadConversations,
    setConversations,
  };
}

export default useConversation;
