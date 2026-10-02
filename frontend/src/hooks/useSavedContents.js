import { useCallback, useEffect, useMemo, useState } from "react";

import useToast from "../components/ui/Toast/useToast";
import {
  deleteSavedContent as deleteSavedContentApi,
  getSavedContents,
  saveContent as saveContentApi,
  unsaveMessage as unsaveMessageApi,
  recordContentActivity,
} from "../services/api/savedContentApi";
import { getUserErrorMessage } from "../utils/apiError";

function useSavedContents() {
  const toast = useToast();
  const [savedContents, setSavedContents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingMessageIds, setPendingMessageIds] = useState([]);

  const loadSavedContents = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getSavedContents();
      setSavedContents(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể tải thư viện nội dung."),
      );
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    // Load the authenticated user's library when the chat workspace opens.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadSavedContents();
  }, [loadSavedContents]);

  const savedMessageIds = useMemo(
    () =>
      new Set(
        savedContents
          .filter((item) => item.message_id != null)
          .map((item) => Number(item.message_id)),
      ),
    [savedContents],
  );

  const markPending = (messageId, pending) => {
    const normalizedId = messageId;
    setPendingMessageIds((current) =>
      pending
        ? [...new Set([...current, normalizedId])]
        : current.filter((id) => id !== normalizedId),
    );
  };

  const saveMessage = async (message) => {
    const messageId = Number(message?.id);
    if (!Number.isInteger(messageId)) {
      toast.warning("Hãy chờ phản hồi được đồng bộ trước khi lưu.");
      return false;
    }
    if (savedMessageIds.has(messageId)) return true;

    markPending(messageId, true);
    try {
      const savedContent = await saveContentApi({ messageId });
      setSavedContents((current) => [
        savedContent,
        ...current.filter((item) => item.id !== savedContent.id),
      ]);
      toast.success("Đã lưu vào Thư viện nội dung.");
      return true;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể lưu nội dung."));
      return false;
    } finally {
      markPending(messageId, false);
    }
  };

  const unsaveMessage = async (messageId) => {
    const normalizedId = Number(messageId);
    markPending(normalizedId, true);
    try {
      await unsaveMessageApi(normalizedId);
      setSavedContents((current) =>
        current.filter((item) => Number(item.message_id) !== normalizedId),
      );
      toast.info("Đã bỏ lưu nội dung.");
      return true;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể bỏ lưu nội dung."));
      return false;
    } finally {
      markPending(normalizedId, false);
    }
  };

  const deleteSavedContent = async (savedContent) => {
    const pendingKey = savedContent.message_id ?? `saved-${savedContent.id}`;
    markPending(pendingKey, true);
    try {
      await deleteSavedContentApi(savedContent.id);
      setSavedContents((current) =>
        current.filter((item) => item.id !== savedContent.id),
      );
      toast.info("Đã xóa khỏi Thư viện nội dung.");
      return true;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể xóa nội dung đã lưu."));
      return false;
    } finally {
      markPending(pendingKey, false);
    }
  };

  const saveGeneratedContent = async ({
    conversationId,
    title,
    content,
    platform,
    platformName = "",
    brandId,
  }) => {
    try {
      const savedContent = await saveContentApi({
        conversationId,
        title,
        content,
        platform,
        platformName,
        brandId,
      });
      setSavedContents((current) => [
        savedContent,
        ...current.filter((item) => item.id !== savedContent.id),
      ]);
      toast.success("Đã lưu phiên bản vào Thư viện nội dung.");
      return true;
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể lưu phiên bản đã chọn."),
      );
      return false;
    }
  };

  const toggleSavedMessage = (message) =>
    savedMessageIds.has(Number(message.id))
      ? unsaveMessage(message.id)
      : saveMessage(message);

  const recordSavedMessageActivity = async (messageId, actionType) => {
    const saved = savedContents.find(
      (item) => Number(item.message_id) === Number(messageId),
    );
    if (!saved) return false;
    try {
      await recordContentActivity(saved.id, actionType);
      return true;
    } catch {
      return false;
    }
  };

  return {
    savedContents,
    savedMessageIds,
    pendingMessageIds: new Set(pendingMessageIds),
    isLoading,
    toggleSavedMessage,
    saveGeneratedContent,
    deleteSavedContent,
    loadSavedContents,
    recordSavedMessageActivity,
  };
}

export default useSavedContents;
