import Modal from "../../ui/Modal/Modal";
import { buildEditorMarkdown, buildLineDiff } from "../../../utils/contentEditor";
import "./VersionCompareModal.css";

const compareDate = (value) => {
  if (!value) return "Bản đang làm việc";
  const normalized =
    typeof value === "string" && !value.endsWith("Z") && !value.includes("+")
      ? `${value}Z`
      : value;
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(normalized));
};

function VersionCompareModal({ open, older, newer, onClose }) {
  const lines = older && newer
    ? buildLineDiff(buildEditorMarkdown(older), buildEditorMarkdown(newer))
    : [];
  return (
    <Modal open={open} title="So sánh phiên bản" size="lg" onClose={onClose}>
      {older && newer && (
        <div className="version-compare">
          <div className="version-compare__labels">
            <strong>Phiên bản {older.version_number}</strong>
            <span>{older.change_summary} · {compareDate(older.created_at)}</span>
            <strong>Phiên bản {newer.version_number}</strong>
            <span>{newer.change_summary || "Nội dung đang làm việc"} · {compareDate(newer.created_at)}</span>
          </div>
          <div className="version-compare__columns">
            <section>
              {lines.map((line) => (
                <pre key={`old-${line.index}`} className={line.changed ? `is-${line.kind}` : ""}>
                  <span>{line.index}</span>{line.before || " "}
                </pre>
              ))}
            </section>
            <section>
              {lines.map((line) => (
                <pre key={`new-${line.index}`} className={line.changed ? `is-${line.kind}` : ""}>
                  <span>{line.index}</span>{line.after || " "}
                </pre>
              ))}
            </section>
          </div>
        </div>
      )}
    </Modal>
  );
}

export default VersionCompareModal;
