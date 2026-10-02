import { useEffect, useMemo, useRef, useState } from "react";
import { FiAlertTriangle, FiFileText } from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useNavigate, useParams } from "react-router-dom";

import AiRewritePanel from "../../components/editor/AiRewritePanel/AiRewritePanel";
import ContentEditorHeader from "../../components/editor/ContentEditorHeader/ContentEditorHeader";
import EditorToolbar from "../../components/editor/EditorToolbar/EditorToolbar";
import VersionCompareModal from "../../components/editor/VersionCompareModal/VersionCompareModal";
import VersionHistoryPanel from "../../components/editor/VersionHistoryPanel/VersionHistoryPanel";
import BrandConsistencyPanel from "../../components/brand/BrandConsistencyPanel/BrandConsistencyPanel";
import ContentScorePanel from "../../components/chat/ContentScorePanel";
import Modal from "../../components/ui/Modal/Modal";
import useToast from "../../components/ui/Toast/useToast";
import useContentEditor from "../../hooks/useContentEditor";
import { getBrands } from "../../services/api/brandApi";
import { checkBrandContent } from "../../services/api/brandApi";
import { getCampaigns } from "../../services/api/campaignApi";
import { evaluateContent } from "../../services/api/contentToolsApi";
import { getUserErrorMessage } from "../../utils/apiError";
import { LEGACY_PLATFORM_LABELS, PLATFORM_OPTIONS, getPlatformLabel } from "../../constants/platforms";
import {
  buildEditorMarkdown,
  exportEditorContent,
} from "../../utils/contentEditor";
import "./ContentEditor.css";

function ContentEditor() {
  const { contentId } = useParams();
  const numericContentId = Number(contentId);
  const navigate = useNavigate();
  const toast = useToast();
  const editor = useContentEditor(numericContentId);
  const contentRef = useRef(null);
  const [campaigns, setCampaigns] = useState([]);
  const [brands, setBrands] = useState([]);
  const [closeRequested, setCloseRequested] = useState(false);
  const [versionModal, setVersionModal] = useState(false);
  const [versionSummary, setVersionSummary] = useState("");
  const [versionSource, setVersionSource] = useState("user");
  const [viewVersion, setViewVersion] = useState(null);
  const [comparePair, setComparePair] = useState(null);
  const [restoreTarget, setRestoreTarget] = useState(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [selection, setSelection] = useState({ start: 0, end: 0, text: "" });
  const [evaluation, setEvaluation] = useState({
    open: false,
    loading: false,
    result: null,
  });
  const [brandCheck, setBrandCheck] = useState({
    open: false,
    loading: false,
    result: null,
  });

  useEffect(() => {
    Promise.all([getCampaigns(), getBrands()])
      .then(([campaignData, brandData]) => {
        setCampaigns(Array.isArray(campaignData) ? campaignData : []);
        setBrands(Array.isArray(brandData) ? brandData : []);
      })
      .catch((error) =>
        toast.error(
          getUserErrorMessage(error, "Không thể tải dữ liệu liên kết của editor."),
        ),
      );
  }, [toast]);

  const selectedBrand = brands.find(
    (brand) => brand.id === Number(editor.draft.brand_id),
  );
  const fullMarkdown = useMemo(
    () => buildEditorMarkdown(editor.draft),
    [editor.draft],
  );
  const forbiddenMatches = useMemo(() => {
    if (!selectedBrand?.forbidden_words?.length) return [];
    const normalized = fullMarkdown.toLocaleLowerCase("vi");
    return selectedBrand.forbidden_words.filter((word) =>
      normalized.includes(word.toLocaleLowerCase("vi")),
    );
  }, [fullMarkdown, selectedBrand]);

  const currentComparable = {
    ...editor.draft,
    version_number: editor.document?.current_version || 1,
    change_summary: editor.dirty
      ? "Nội dung đang chỉnh sửa, chưa tạo phiên bản"
      : "Phiên bản hiện tại",
    created_at: editor.document?.updated_at,
  };

  const closeEditor = () => {
    if (editor.dirty) {
      setCloseRequested(true);
      return;
    }
    navigate(editor.document?.source_conversation_id ? "/chat" : "/library");
  };

  const copy = async (item = editor.draft) => {
    try {
      await navigator.clipboard.writeText(buildEditorMarkdown(item));
      toast.success("Đã sao chép nội dung.");
    } catch {
      toast.error("Không thể sao chép nội dung.");
    }
  };

  const openAi = () => {
    const textarea = contentRef.current;
    const start = textarea?.selectionStart ?? 0;
    const end = textarea?.selectionEnd ?? 0;
    setSelection({
      start,
      end,
      text: end > start ? editor.draft.content.slice(start, end) : "",
    });
    setAiOpen(true);
  };

  const applyAi = (action, mode, suggestion) => {
    if (action === "new_title") {
      editor.updateField("title", suggestion.trim());
    } else if (action === "add_hashtags") {
      editor.updateField("hashtags", suggestion.trim());
    } else if (action === "improve_cta") {
      editor.updateField("cta", suggestion.trim());
    } else if (mode === "selection" && selection.end > selection.start) {
      editor.updateField(
        "content",
        `${editor.draft.content.slice(0, selection.start)}${suggestion}${editor.draft.content.slice(selection.end)}`,
      );
    } else if (mode === "append") {
      editor.updateField(
        "content",
        `${editor.draft.content.trimEnd()}\n\n${suggestion}`,
      );
    } else {
      editor.updateField("content", suggestion);
    }
    setAiOpen(false);
    setVersionSource("ai");
    toast.info("Đã áp dụng đề xuất. Nội dung đang ở trạng thái chưa lưu.");
  };

  const evaluate = async () => {
    setEvaluation({ open: true, loading: true, result: null });
    try {
      const result = await evaluateContent({
        content: fullMarkdown,
        platform: editor.draft.platform || null,
        platformName: editor.draft.platform_name || null,
      });
      setEvaluation({ open: true, loading: false, result });
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể đánh giá nội dung."));
      setEvaluation({ open: false, loading: false, result: null });
    }
  };

  const checkBrand = async () => {
    if (!editor.draft.brand_id) return;
    setBrandCheck({ open: true, loading: true, result: null });
    try {
      const result = await checkBrandContent(
        Number(editor.draft.brand_id),
        fullMarkdown,
        editor.draft.platform || null,
      );
      setBrandCheck({ open: true, loading: false, result });
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể kiểm tra thương hiệu."),
      );
      setBrandCheck({ open: false, loading: false, result: null });
    }
  };

  if (editor.loading) {
    return (
      <div className="content-editor-loading">
        <FiFileText />
        <strong>Đang mở trình soạn thảo...</strong>
      </div>
    );
  }

  if (editor.error || !editor.document) {
    return (
      <div className="content-editor-loading is-error">
        <FiAlertTriangle />
        <strong>{editor.error || "Không tìm thấy nội dung."}</strong>
        <button type="button" onClick={() => navigate("/chat")}>Quay lại Chat</button>
      </div>
    );
  }

  return (
    <div className="content-editor-page">
      <ContentEditorHeader
        document={{
          ...editor.document,
          brand_name: selectedBrand?.name || editor.document.brand_name,
          campaign_name:
            campaigns.find((item) => item.id === Number(editor.draft.campaign_id))?.name ||
            editor.document.campaign_name,
        }}
        draft={editor.draft}
        saveStatus={editor.saveStatus}
        onClose={closeEditor}
      />
      <EditorToolbar
        saveStatus={editor.saveStatus}
        dirty={editor.dirty}
        campaigns={campaigns}
        campaignId={editor.draft.campaign_id}
        isPrimary={editor.draft.is_campaign_primary}
        hasBrand={Boolean(editor.draft.brand_id)}
        onSave={editor.persistDraft}
        onSaveVersion={() => setVersionModal(true)}
        onUndo={editor.resetUnsaved}
        onCopy={copy}
        onExport={(format) =>
          exportEditorContent(
            format,
            editor.draft,
            editor.document.current_version,
          ).catch((error) => toast.error(error.message))
        }
        onEvaluate={evaluate}
        onBrandCheck={checkBrand}
        onAiRewrite={openAi}
        onCampaignChange={(value) => {
          editor.updateField("campaign_id", value || "");
          if (!value) editor.updateField("is_campaign_primary", false);
        }}
        onPrimaryChange={(value) => editor.updateField("is_campaign_primary", value)}
      />

      <main className="content-editor-page__workspace">
        <section className="content-editor-form">
          <div className="content-editor-form__meta">
            <label>
              Trạng thái
              <select value={editor.draft.status} onChange={(event) => editor.updateField("status", event.target.value)}>
                <option value="draft">Bản nháp</option>
                <option value="ready">Sẵn sàng</option>
                <option value="archived">Lưu trữ</option>
              </select>
            </label>
            <label>
              Nền tảng
              <select
                value={editor.draft.platform || ""}
                onChange={(event) => {
                  const value = event.target.value;
                  editor.updateField("platform", value);
                  if (value !== "other") editor.updateField("platform_name", "");
                }}
              >
                <option value="">Nội dung chung</option>
                {editor.draft.platform && !PLATFORM_OPTIONS.some((item) => item.value === editor.draft.platform) && (
                  <option value={editor.draft.platform}>
                    Nền tảng cũ: {getPlatformLabel(editor.draft.platform, editor.draft.platform_name)}
                  </option>
                )}
                {PLATFORM_OPTIONS.map((item) => (
                  <option value={item.value} key={item.value}>{item.label}</option>
                ))}
              </select>
              {editor.draft.platform === "other" && (
                <input
                  value={editor.draft.platform_name || ""}
                  maxLength={80}
                  placeholder="Tên nền tảng hoặc nơi đăng nội dung"
                  onChange={(event) => editor.updateField("platform_name", event.target.value)}
                  required
                />
              )}
            </label>
            <label>
              Thương hiệu
              <select value={editor.draft.brand_id || ""} onChange={(event) => editor.updateField("brand_id", event.target.value ? Number(event.target.value) : "")}>
                <option value="">Không dùng thương hiệu</option>
                {brands.map((brand) => (
                  <option key={brand.id} value={brand.id}>{brand.name}</option>
                ))}
              </select>
            </label>
          </div>

          {selectedBrand && (
            <div className="content-editor-brand">
              <div>
                <strong>{selectedBrand.name}</strong>
                <span>Giọng điệu: {selectedBrand.default_tone || "Chưa cấu hình"}</span>
                <span>CTA mặc định: {selectedBrand.preferred_cta || "Chưa cấu hình"}</span>
              </div>
              {forbiddenMatches.length > 0 && (
                <p>
                  <FiAlertTriangle />
                  Có từ không được dùng: {forbiddenMatches.join(", ")}
                </p>
              )}
            </div>
          )}

          <label className="content-editor-form__field">
            Tiêu đề
            <input
              value={editor.draft.title}
              maxLength={160}
              onChange={(event) => editor.updateField("title", event.target.value)}
            />
          </label>
          <label className="content-editor-form__field is-content">
            Nội dung chính
            <textarea
              ref={contentRef}
              value={editor.draft.content}
              rows={18}
              onChange={(event) => editor.updateField("content", event.target.value)}
            />
            <small>{editor.draft.content.length.toLocaleString("vi-VN")} ký tự · hỗ trợ Markdown</small>
          </label>
          <div className="content-editor-form__secondary">
            <label className="content-editor-form__field">
              CTA
              <textarea rows={3} value={editor.draft.cta || ""} onChange={(event) => editor.updateField("cta", event.target.value)} />
            </label>
            <label className="content-editor-form__field">
              Hashtag
              <textarea rows={3} value={editor.draft.hashtags || ""} onChange={(event) => editor.updateField("hashtags", event.target.value)} />
            </label>
          </div>
          <label className="content-editor-form__field">
            Ghi chú nội bộ
            <textarea rows={4} value={editor.draft.internal_notes || ""} onChange={(event) => editor.updateField("internal_notes", event.target.value)} />
            <small>Ghi chú không được đưa vào nội dung xuất.</small>
          </label>

          {editor.campaignContents.length > 0 && (
            <section className="content-editor-related">
              <h2>Nội dung khác trong cùng chiến dịch</h2>
              <div>
                {editor.campaignContents.map((item) => (
                  <button type="button" key={item.id} onClick={() => navigate(`/contents/${item.id}`)}>
                    <strong>{item.title}</strong>
                    <span>Phiên bản {item.current_version}</span>
                  </button>
                ))}
              </div>
            </section>
          )}
        </section>

        <VersionHistoryPanel
          versions={editor.versions}
          currentVersion={editor.document.current_version}
          onView={setViewVersion}
          onCompare={(version) =>
            setComparePair({ older: version, newer: currentComparable })
          }
          onCompareSelected={(versions) => {
            const ordered = [...versions].sort(
              (left, right) => left.version_number - right.version_number,
            );
            setComparePair({ older: ordered[0], newer: ordered[1] });
          }}
          onRestore={setRestoreTarget}
          onCopy={copy}
          onExport={(version) =>
            exportEditorContent("markdown", version, version.version_number)
          }
        />
      </main>

      <AiRewritePanel
        open={aiOpen}
        contentId={numericContentId}
        selectedText={selection.text}
        onApply={applyAi}
        onClose={() => setAiOpen(false)}
      />
      <VersionCompareModal
        open={Boolean(comparePair)}
        older={comparePair?.older}
        newer={comparePair?.newer}
        onClose={() => setComparePair(null)}
      />
      <Modal open={Boolean(viewVersion)} title={`Phiên bản ${viewVersion?.version_number || ""}`} size="lg" onClose={() => setViewVersion(null)}>
        <div className="content-editor-version-view">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {viewVersion ? buildEditorMarkdown(viewVersion) : ""}
          </ReactMarkdown>
        </div>
      </Modal>
      <Modal
        open={versionModal}
        title="Lưu thành phiên bản mới"
        onClose={() => setVersionModal(false)}
        footer={
          <div className="content-editor-modal-actions">
            <button type="button" onClick={() => setVersionModal(false)}>Hủy</button>
            <button type="button" className="is-primary" onClick={async () => {
              const result = await editor.saveVersion(versionSummary, versionSource);
              if (result) {
                setVersionModal(false);
                setVersionSummary("");
                setVersionSource("user");
              }
            }}>Tạo phiên bản</button>
          </div>
        }
      >
        <label className="content-editor-modal-field">
          Tóm tắt thay đổi (không bắt buộc)
          <input value={versionSummary} maxLength={500} placeholder="Ví dụ: Điều chỉnh CTA và giọng văn" onChange={(event) => setVersionSummary(event.target.value)} />
        </label>
      </Modal>
      <Modal
        open={Boolean(restoreTarget)}
        title="Khôi phục phiên bản?"
        onClose={() => setRestoreTarget(null)}
        footer={
          <div className="content-editor-modal-actions">
            <button type="button" onClick={() => setRestoreTarget(null)}>Hủy</button>
            <button type="button" className="is-primary" onClick={async () => {
              if (await editor.restoreVersion(restoreTarget.id)) setRestoreTarget(null);
            }}>Khôi phục và tạo phiên bản mới</button>
          </div>
        }
      >
        <p>Phiên bản {restoreTarget?.version_number} sẽ trở thành nội dung hiện tại. Các phiên bản mới hơn vẫn được giữ nguyên.</p>
      </Modal>
      <Modal
        open={closeRequested}
        title="Bạn có thay đổi chưa lưu"
        onClose={() => setCloseRequested(false)}
        footer={
          <div className="content-editor-modal-actions">
            <button type="button" onClick={() => setCloseRequested(false)}>Tiếp tục chỉnh sửa</button>
            <button type="button" className="is-danger" onClick={() => {
              editor.resetUnsaved();
              navigate(editor.document.source_conversation_id ? "/chat" : "/library");
            }}>Bỏ thay đổi và đóng</button>
            <button type="button" className="is-primary" onClick={async () => {
              if ((await editor.persistDraft())?.fullySaved) {
                navigate(editor.document.source_conversation_id ? "/chat" : "/library");
              }
            }}>Lưu và đóng</button>
          </div>
        }
      >
        <p>Bản nháp trên thiết bị vẫn được giữ nếu lưu thất bại.</p>
      </Modal>
      <Modal
        open={Boolean(editor.localRecovery)}
        title="Phát hiện bản nháp mới hơn"
        closeDisabled
        footer={
          <div className="content-editor-modal-actions">
            <button type="button" onClick={editor.discardLocal}>Dùng bản trên máy chủ</button>
            <button type="button" className="is-primary" onClick={editor.recoverLocal}>Khôi phục bản nháp</button>
          </div>
        }
      >
        <p>Bản nháp lưu trên thiết bị mới hơn nội dung trên máy chủ. Chọn bản bạn muốn tiếp tục.</p>
      </Modal>
      <ContentScorePanel
        open={evaluation.open}
        loading={evaluation.loading}
        result={evaluation.result}
        onClose={() => setEvaluation({ open: false, loading: false, result: null })}
      />
      <BrandConsistencyPanel
        open={brandCheck.open}
        loading={brandCheck.loading}
        result={brandCheck.result}
        brandName={selectedBrand?.name}
        onClose={() => setBrandCheck({ open: false, loading: false, result: null })}
      />
    </div>
  );
}

export default ContentEditor;
