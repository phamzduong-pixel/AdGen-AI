import {
  FiBarChart2,
  FiCheckCircle,
  FiCopy,
  FiDownload,
  FiRefreshCw,
  FiSave,
  FiShield,
  FiStar,
  FiZap,
} from "react-icons/fi";
import "./EditorToolbar.css";

function EditorToolbar({
  saveStatus,
  dirty,
  campaigns = [],
  campaignId,
  isPrimary,
  hasBrand,
  onSave,
  onSaveVersion,
  onUndo,
  onCopy,
  onExport,
  onEvaluate,
  onBrandCheck,
  onAiRewrite,
  onCampaignChange,
  onPrimaryChange,
}) {
  const busy = saveStatus === "saving";
  return (
    <div className="editor-toolbar">
      <div className="editor-toolbar__group">
        <button type="button" className="is-primary" onClick={onSave} disabled={busy || !dirty}>
          <FiSave /> Lưu
        </button>
        <button type="button" onClick={onSaveVersion} disabled={busy}>
          <FiCheckCircle /> Lưu thành bản mới
        </button>
        <button type="button" onClick={onUndo} disabled={busy || !dirty}>
          <FiRefreshCw /> Hoàn tác
        </button>
      </div>
      <div className="editor-toolbar__group">
        <button type="button" onClick={onAiRewrite} disabled={busy}>
          <FiZap /> Trợ lý AI
        </button>
        <button type="button" onClick={onEvaluate} disabled={busy}>
          <FiBarChart2 /> Đánh giá
        </button>
        {hasBrand && (
          <button type="button" onClick={onBrandCheck} disabled={busy}>
            <FiShield /> Kiểm tra thương hiệu
          </button>
        )}
        <button type="button" onClick={onCopy}>
          <FiCopy /> Sao chép
        </button>
        <label className="editor-toolbar__export">
          <FiDownload />
          <select defaultValue="" onChange={(event) => {
            if (event.target.value) onExport(event.target.value);
            event.target.value = "";
          }}>
            <option value="" disabled>Xuất</option>
            <option value="txt">TXT</option>
            <option value="markdown">Markdown</option>
            <option value="pdf">PDF</option>
          </select>
        </label>
      </div>
      <div className="editor-toolbar__campaign">
        <select
          value={campaignId ?? ""}
          onChange={(event) => onCampaignChange(event.target.value ? Number(event.target.value) : null)}
          disabled={busy}
          aria-label="Gắn vào chiến dịch"
        >
          <option value="">Không thuộc chiến dịch</option>
          {campaigns.map((campaign) => (
            <option key={campaign.id} value={campaign.id}>{campaign.name}</option>
          ))}
        </select>
        <label>
          <input
            type="checkbox"
            checked={Boolean(isPrimary)}
            disabled={!campaignId || busy}
            onChange={(event) => onPrimaryChange(event.target.checked)}
          />
          <FiStar /> Bản chính
        </label>
      </div>
    </div>
  );
}

export default EditorToolbar;
