import { FiFileText, FiVideo, FiX } from "react-icons/fi";

const formatSize = (size) =>
  size < 1024 * 1024
    ? `${Math.ceil(size / 1024)} KB`
    : `${(size / (1024 * 1024)).toFixed(1)} MB`;

function AttachmentPreview({ files, onRemove }) {
  if (!files.length) return null;

  return (
    <div className="attachment-preview">
      {files.map((item) => {
        const isImage = item.file.type.startsWith("image/");
        const isVideo =
          item.file.type.startsWith("video/") ||
          /\.(mp4|mov|webm)$/i.test(item.file.name);

        return (
          <div className="attachment-preview__item" key={item.id}>
            {isImage ? (
              <img src={item.previewUrl} alt={item.file.name} />
            ) : isVideo ? (
              <span className="attachment-preview__document attachment-preview__video">
                <FiVideo />
              </span>
            ) : (
              <span className="attachment-preview__document">
                <FiFileText />
              </span>
            )}

            <span className="attachment-preview__details">
              <strong>{item.file.name}</strong>
              <small>{formatSize(item.file.size)}</small>
            </span>

            <button
              type="button"
              onClick={() => onRemove(item.id)}
              aria-label={`Bỏ tệp ${item.file.name}`}
            >
              <FiX />
            </button>
          </div>
        );
      })}
    </div>
  );
}

export default AttachmentPreview;
