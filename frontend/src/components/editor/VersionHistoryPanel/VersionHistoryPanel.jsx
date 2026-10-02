import {
  FiClock,
  FiCopy,
  FiDownload,
  FiEye,
  FiGitCommit,
  FiRotateCcw,
} from "react-icons/fi";
import { useState } from "react";
import "./VersionHistoryPanel.css";

const formatDate = (value) => {
  const normalized =
    typeof value === "string" && !value.endsWith("Z") && !value.includes("+")
      ? `${value}Z`
      : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime())
    ? ""
    : new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(date);
};

function VersionHistoryPanel({
  versions = [],
  currentVersion,
  onView,
  onCompare,
  onCompareSelected,
  onRestore,
  onCopy,
  onExport,
}) {
  const [selectedIds, setSelectedIds] = useState([]);
  const toggleSelected = (versionId) =>
    setSelectedIds((current) =>
      current.includes(versionId)
        ? current.filter((id) => id !== versionId)
        : current.length < 2
          ? [...current, versionId]
          : current,
    );
  return (
    <aside className="version-history">
      <header>
        <div>
          <span><FiClock /></span>
          <div>
            <h2>Lịch sử phiên bản</h2>
            <p>{versions.length} phiên bản bất biến</p>
          </div>
          <button
            type="button"
            className="version-history__compare-selected"
            disabled={selectedIds.length !== 2}
            onClick={() => {
              onCompareSelected?.(
                selectedIds.map((id) => versions.find((item) => item.id === id)),
              );
              setSelectedIds([]);
            }}
          >
            So sánh ({selectedIds.length}/2)
          </button>
        </div>
      </header>
      <div className="version-history__list">
        {versions.map((version) => (
          <article
            key={version.id}
            className={version.version_number === currentVersion ? "is-current" : ""}
          >
            <div className="version-history__title">
              <label>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(version.id)}
                  onChange={() => toggleSelected(version.id)}
                />
                <strong>Phiên bản {version.version_number}</strong>
              </label>
              {version.version_number === currentVersion && <span>Hiện tại</span>}
            </div>
            <p>{version.change_summary}</p>
            <small>
              {version.created_by === "ai"
                ? "AI"
                : version.created_by === "restore"
                  ? "Khôi phục"
                  : "Bạn"} · {formatDate(version.created_at)}
            </small>
            <div className="version-history__actions">
              <button type="button" onClick={() => onView(version)} title="Xem"><FiEye /></button>
              <button type="button" onClick={() => onCompare(version)} title="So sánh"><FiGitCommit /></button>
              <button type="button" onClick={() => onCopy(version)} title="Sao chép"><FiCopy /></button>
              <button type="button" onClick={() => onExport(version)} title="Xuất Markdown"><FiDownload /></button>
              <button type="button" onClick={() => onRestore(version)} title="Khôi phục"><FiRotateCcw /></button>
            </div>
          </article>
        ))}
      </div>
    </aside>
  );
}

export default VersionHistoryPanel;
