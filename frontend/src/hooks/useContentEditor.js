import { useCallback, useEffect, useRef, useState } from "react";

import useToast from "../components/ui/Toast/useToast";
import {
  createContentVersion,
  getCampaignContentDocuments,
  getContentDocument,
  getContentVersions,
  restoreContentVersion,
  updateContentDocument,
} from "../services/api/contentEditorApi";
import { getUserErrorMessage } from "../utils/apiError";
import {
  editorDraftEquals,
  editorDraftKey,
  normalizeEditorDraft,
  parseLocalEditorDraft,
} from "../utils/contentEditor";

const parseServerTime = (value) => {
  if (!value) return 0;
  const normalized =
    typeof value === "string" && !value.endsWith("Z") && !value.includes("+")
      ? `${value}Z`
      : value;
  return new Date(normalized).getTime() || 0;
};

const apiDraft = (draft) => ({
  ...draft,
  title: draft.title.trim(),
  content: draft.content.trim(),
  cta: draft.cta?.trim() || null,
  hashtags: draft.hashtags?.trim() || null,
  internal_notes: draft.internal_notes?.trim() || null,
  platform: draft.platform || null,
  platform_name: draft.platform === "other" ? draft.platform_name?.trim() || null : null,
  brand_id: draft.brand_id ? Number(draft.brand_id) : null,
  campaign_id: draft.campaign_id ? Number(draft.campaign_id) : null,
  is_campaign_primary: Boolean(draft.campaign_id && draft.is_campaign_primary),
});

function useContentEditor(contentId) {
  const toast = useToast();
  const [document, setDocument] = useState(null);
  const [draft, setDraft] = useState(() => normalizeEditorDraft());
  const [serverDraft, setServerDraft] = useState(() => normalizeEditorDraft());
  const [versions, setVersions] = useState([]);
  const [campaignContents, setCampaignContents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState("idle");
  const [localRecovery, setLocalRecovery] = useState(null);
  const [error, setError] = useState("");
  const draftRef = useRef(draft);
  const dirtyRef = useRef(false);
  const savingRef = useRef(false);

  const applyDraft = useCallback((next, isDirty = false) => {
    const normalized = normalizeEditorDraft(next);
    draftRef.current = normalized;
    dirtyRef.current = isDirty;
    setDraft(normalized);
    setDirty(isDirty);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [loadedDocument, loadedVersions, related] = await Promise.all([
        getContentDocument(contentId),
        getContentVersions(contentId),
        getCampaignContentDocuments(contentId),
      ]);
      const normalized = normalizeEditorDraft(loadedDocument);
      setDocument(loadedDocument);
      setServerDraft(normalized);
      applyDraft(normalized, false);
      setVersions(Array.isArray(loadedVersions) ? loadedVersions : []);
      setCampaignContents(Array.isArray(related) ? related : []);
      setSaveStatus("saved");

      const local = parseLocalEditorDraft(
        localStorage.getItem(editorDraftKey(contentId)),
      );
      if (
        local &&
        local.savedAt > parseServerTime(loadedDocument.updated_at) &&
        !editorDraftEquals(local.draft, normalized)
      ) {
        setLocalRecovery(local);
      } else if (local) {
        localStorage.removeItem(editorDraftKey(contentId));
      }
    } catch (loadError) {
      const message = getUserErrorMessage(
        loadError,
        "Không thể mở trình soạn thảo nội dung.",
      );
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [applyDraft, contentId, toast]);

  useEffect(() => {
    // Synchronize the editor with its protected server document.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const updateField = useCallback(
    (field, value) => {
      const next = { ...draftRef.current, [field]: value };
      applyDraft(next, true);
      setSaveStatus("unsaved");
      localStorage.setItem(
        editorDraftKey(contentId),
        JSON.stringify({ savedAt: Date.now(), draft: next }),
      );
    },
    [applyDraft, contentId],
  );

  const persistDraft = useCallback(async () => {
    if (savingRef.current || !dirtyRef.current) return null;
    const snapshot = normalizeEditorDraft(draftRef.current);
    if (!snapshot.title.trim() || !snapshot.content.trim()) {
      setSaveStatus("error");
      return null;
    }
    savingRef.current = true;
    setSaveStatus("saving");
    try {
      const updated = await updateContentDocument(contentId, apiDraft(snapshot));
      const normalizedServer = normalizeEditorDraft(updated);
      setDocument(updated);
      setServerDraft(normalizedServer);
      const fullySaved = editorDraftEquals(draftRef.current, snapshot);
      if (fullySaved) {
        applyDraft(normalizedServer, false);
        localStorage.removeItem(editorDraftKey(contentId));
      } else {
        setDraft({ ...draftRef.current });
      }
      setSaveStatus(fullySaved ? "saved" : "unsaved");
      return { document: updated, fullySaved };
    } catch (saveError) {
      setSaveStatus("error");
      toast.error(
        getUserErrorMessage(
          saveError,
          "Không thể tự động lưu. Bản nháp vẫn được giữ trên thiết bị.",
        ),
      );
      return null;
    } finally {
      savingRef.current = false;
    }
  }, [applyDraft, contentId, toast]);

  useEffect(() => {
    if (!dirty) return undefined;
    const timer = window.setTimeout(persistDraft, 1500);
    return () => window.clearTimeout(timer);
  }, [dirty, draft, persistDraft]);

  useEffect(() => {
    const warn = (event) => {
      if (!dirtyRef.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);

  const resetUnsaved = useCallback(() => {
    applyDraft(serverDraft, false);
    localStorage.removeItem(editorDraftKey(contentId));
    setSaveStatus("saved");
  }, [applyDraft, contentId, serverDraft]);

  const saveVersion = useCallback(
    async (summary, createdBy = "user") => {
      if (savingRef.current) return null;
      if (dirtyRef.current) {
        const saved = await persistDraft();
        if (!saved?.fullySaved) {
          if (saved) {
            toast.info("Có thay đổi mới trong khi lưu. Hãy lưu lại trước khi tạo phiên bản.");
          }
          return null;
        }
      }
      savingRef.current = true;
      setSaveStatus("saving");
      try {
        const result = await createContentVersion(
          contentId,
          summary,
          createdBy,
        );
        setDocument(result.document);
        setVersions(await getContentVersions(contentId));
        setSaveStatus("saved");
        toast[result.created ? "success" : "info"](
          result.created
            ? `Đã tạo phiên bản ${result.version.version_number}.`
            : "Nội dung không thay đổi nên không tạo phiên bản mới.",
        );
        return result;
      } catch (versionError) {
        setSaveStatus("error");
        toast.error(
          getUserErrorMessage(versionError, "Không thể tạo phiên bản mới."),
        );
        return null;
      } finally {
        savingRef.current = false;
      }
    },
    [contentId, persistDraft, toast],
  );

  const restoreVersion = useCallback(
    async (versionId) => {
      if (savingRef.current) return null;
      savingRef.current = true;
      setSaveStatus("saving");
      try {
        const result = await restoreContentVersion(contentId, versionId);
        const normalized = normalizeEditorDraft(result.document);
        setDocument(result.document);
        setServerDraft(normalized);
        applyDraft(normalized, false);
        setVersions(await getContentVersions(contentId));
        localStorage.removeItem(editorDraftKey(contentId));
        setSaveStatus("saved");
        toast.success(
          `Đã khôi phục và tạo phiên bản ${result.version.version_number}.`,
        );
        return result;
      } catch (restoreError) {
        setSaveStatus("error");
        toast.error(
          getUserErrorMessage(restoreError, "Không thể khôi phục phiên bản."),
        );
        return null;
      } finally {
        savingRef.current = false;
      }
    },
    [applyDraft, contentId, toast],
  );

  const recoverLocal = useCallback(() => {
    if (!localRecovery) return;
    applyDraft(localRecovery.draft, true);
    setLocalRecovery(null);
    setSaveStatus("unsaved");
  }, [applyDraft, localRecovery]);

  const discardLocal = useCallback(() => {
    localStorage.removeItem(editorDraftKey(contentId));
    setLocalRecovery(null);
    applyDraft(serverDraft, false);
  }, [applyDraft, contentId, serverDraft]);

  return {
    document,
    draft,
    versions,
    campaignContents,
    loading,
    dirty,
    saveStatus,
    localRecovery,
    error,
    updateField,
    persistDraft,
    resetUnsaved,
    saveVersion,
    restoreVersion,
    recoverLocal,
    discardLocal,
    reload: load,
  };
}

export default useContentEditor;
