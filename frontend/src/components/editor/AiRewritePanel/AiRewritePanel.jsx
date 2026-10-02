import { useEffect, useState } from "react";
import { FiLoader, FiZap } from "react-icons/fi";

import Modal from "../../ui/Modal/Modal";
import useToast from "../../ui/Toast/useToast";
import { rewriteContent } from "../../../services/api/contentEditorApi";
import { getUserErrorMessage } from "../../../utils/apiError";
import "./AiRewritePanel.css";

const ACTIONS = [
  ["shorter", "Viết ngắn hơn"],
  ["longer", "Viết dài hơn"],
  ["professional", "Chuyên nghiệp hơn"],
  ["friendly", "Thân thiện hơn"],
  ["spelling", "Sửa chính tả"],
  ["improve_cta", "Cải thiện CTA"],
  ["new_title", "Tạo tiêu đề mới"],
  ["add_hashtags", "Thêm hashtag"],
  ["align_brand", "Theo thương hiệu"],
  ["alternative", "Phương án khác"],
];

function AiRewritePanel({
  open,
  contentId,
  selectedText,
  onApply,
  onClose,
}) {
  const toast = useToast();
  const [action, setAction] = useState("shorter");
  const [suggestion, setSuggestion] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    // A new editor request starts with a clean proposal.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSuggestion("");
  }, [open, selectedText]);

  const generate = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const result = await rewriteContent(contentId, action, selectedText);
      setSuggestion(result.suggestion);
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể tạo đề xuất AI."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      title="Trợ lý biên tập AI"
      size="lg"
      onClose={onClose}
      closeDisabled={loading}
    >
      <div className="ai-rewrite">
        <div className="ai-rewrite__scope">
          <strong>{selectedText ? "Đoạn đang chọn" : "Toàn bộ nội dung"}</strong>
          <p>
            {selectedText
              ? selectedText.slice(0, 240)
              : "AI sẽ tạo đề xuất nhưng không tự ghi đè nội dung."}
          </p>
        </div>
        <div className="ai-rewrite__controls">
          <select value={action} onChange={(event) => setAction(event.target.value)}>
            {ACTIONS.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <button type="button" onClick={generate} disabled={loading}>
            {loading ? <FiLoader className="is-spinning" /> : <FiZap />}
            {loading ? "Đang tạo..." : "Tạo đề xuất"}
          </button>
        </div>
        {suggestion && (
          <div className="ai-rewrite__result">
            <h3>Đề xuất</h3>
            <textarea value={suggestion} onChange={(event) => setSuggestion(event.target.value)} rows={10} />
            <div>
              {selectedText && (
                <button type="button" onClick={() => onApply(action, "selection", suggestion)}>
                  Áp dụng vào đoạn chọn
                </button>
              )}
              <button type="button" onClick={() => onApply(action, "append", suggestion)}>
                Chèn thêm
              </button>
              <button type="button" className="is-primary" onClick={() => onApply(action, "replace", suggestion)}>
                Thay thế toàn bộ
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

export default AiRewritePanel;
