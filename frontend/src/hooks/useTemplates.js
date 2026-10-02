import { useCallback, useEffect, useMemo, useState } from "react";

import useToast from "../components/ui/Toast/useToast";
import { PLATFORM_OPTIONS } from "../constants/platforms";
import {
  createCustomTemplate,
  deleteCustomTemplate,
  favoriteTemplate,
  getTemplates,
  unfavoriteTemplate,
  updateCustomTemplate,
} from "../services/api/templateApi";
import { getUserErrorMessage } from "../utils/apiError";

function useTemplates() {
  const toast = useToast();
  const [templates, setTemplates] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingIds, setPendingIds] = useState([]);

  const loadTemplates = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getTemplates();
      setTemplates(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể tải thư viện mẫu."));
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    // Load the authenticated user's accessible templates on page entry.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadTemplates();
  }, [loadTemplates]);

  const markPending = (templateId, pending) => {
    setPendingIds((current) =>
      pending
        ? [...new Set([...current, templateId])]
        : current.filter((id) => id !== templateId),
    );
  };

  const toggleFavorite = async (template) => {
    if (pendingIds.includes(template.id)) return;
    const nextFavorite = !template.is_favorite;
    markPending(template.id, true);
    setTemplates((current) =>
      current.map((item) =>
        item.id === template.id
          ? { ...item, is_favorite: nextFavorite }
          : item,
      ),
    );
    try {
      const updated = nextFavorite
        ? await favoriteTemplate(template.id)
        : await unfavoriteTemplate(template.id);
      setTemplates((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (error) {
      setTemplates((current) =>
        current.map((item) =>
          item.id === template.id
            ? { ...item, is_favorite: template.is_favorite }
            : item,
        ),
      );
      toast.error(
        getUserErrorMessage(error, "Không thể cập nhật mẫu yêu thích."),
      );
    } finally {
      markPending(template.id, false);
    }
  };

  const createTemplate = async (payload) => {
    try {
      const created = await createCustomTemplate(payload);
      setTemplates((current) => [created, ...current]);
      toast.success("Đã tạo mẫu cá nhân.");
      return created;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể tạo mẫu."));
      return null;
    }
  };

  const updateTemplate = async (templateId, payload) => {
    markPending(templateId, true);
    try {
      const updated = await updateCustomTemplate(templateId, payload);
      setTemplates((current) =>
        current.map((item) => (item.id === templateId ? updated : item)),
      );
      toast.success("Đã cập nhật mẫu.");
      return updated;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể cập nhật mẫu."));
      return null;
    } finally {
      markPending(templateId, false);
    }
  };

  const deleteTemplate = async (templateId) => {
    markPending(templateId, true);
    try {
      await deleteCustomTemplate(templateId);
      setTemplates((current) =>
        current.filter((item) => item.id !== templateId),
      );
      toast.success("Đã xóa mẫu cá nhân.");
      return true;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể xóa mẫu."));
      return false;
    } finally {
      markPending(templateId, false);
    }
  };

  const platforms = useMemo(
    () => PLATFORM_OPTIONS.map((item) => item.value),
    [],
  );
  const categories = useMemo(
    () => [...new Set(templates.map((item) => item.category))].sort(),
    [templates],
  );

  return {
    templates,
    platforms,
    categories,
    isLoading,
    pendingIds: new Set(pendingIds),
    reload: loadTemplates,
    toggleFavorite,
    createTemplate,
    updateTemplate,
    deleteTemplate,
  };
}

export default useTemplates;
