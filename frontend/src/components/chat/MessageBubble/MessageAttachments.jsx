import { useState } from "react";
import { FiDownload, FiFileText, FiImage, FiVideo, FiX } from "react-icons/fi";
import { createPortal } from "react-dom";

import { downloadAttachment } from "../../../services/api/uploadApi";
import useToast from "../../ui/Toast/useToast";

const formatSize = (size = 0) =>
  size < 1024 * 1024
    ? `${Math.max(1, Math.ceil(size / 1024))} KB`
    : `${(size / (1024 * 1024)).toFixed(1)} MB`;

function MessageAttachments({ attachments }) {
  const toast = useToast();
  const [mediaViewer, setMediaViewer] = useState(null);
  const [loadingId, setLoadingId] = useState(null);

  if (!attachments?.length) return null;

  const openAttachment = async (attachment) => {
    setLoadingId(attachment.id);
    try {
      const blob = await downloadAttachment(attachment.id);
      const objectUrl = URL.createObjectURL(blob);

      const isImage = attachment.content_type?.startsWith("image/");
      const isVideo =
        attachment.content_type?.startsWith("video/") ||
        attachment.file_type === "video" ||
        /\.(mp4|mov|webm)$/i.test(attachment.filename);

      if (isImage) {
        setMediaViewer({ ...attachment, objectUrl, type: "image" });
      } else if (isVideo) {
        setMediaViewer({ ...attachment, objectUrl, type: "video" });
      } else {
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = attachment.filename;
        link.click();
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      }
    } catch {
      toast.error("Không thể mở tệp đính kèm. Tệp có thể đã bị xóa.");
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <>
      <div className="message-attachments">
        {attachments.map((attachment) => {
          const isImage = attachment.content_type?.startsWith("image/");
          const isVideo =
            attachment.content_type?.startsWith("video/") ||
            attachment.file_type === "video" ||
            /\.(mp4|mov|webm)$/i.test(attachment.filename);

          return (
            <button
              type="button"
              className="message-attachment"
              key={attachment.id}
              onClick={() => openAttachment(attachment)}
              disabled={loadingId === attachment.id}
            >
              <span className="message-attachment__icon">
                {isImage ? (
                  <FiImage />
                ) : isVideo ? (
                  <FiVideo />
                ) : (
                  <FiFileText />
                )}
              </span>
              <span>
                <strong>{attachment.filename}</strong>
                <small>{formatSize(attachment.size)}</small>
              </span>
              <FiDownload />
            </button>
          );
        })}
      </div>

      {mediaViewer &&
        createPortal(
          <div className="image-viewer" role="dialog" aria-modal="true">
            <button
              type="button"
              className="image-viewer__backdrop"
              onClick={() => {
                URL.revokeObjectURL(mediaViewer.objectUrl);
                setMediaViewer(null);
              }}
              aria-label="Đóng"
            />
            {mediaViewer.type === "video" ? (
              <video
                src={mediaViewer.objectUrl}
                controls
                autoPlay
                className="media-viewer__video"
                style={{ maxWidth: "90vw", maxHeight: "80vh", borderRadius: "8px" }}
              />
            ) : (
              <img src={mediaViewer.objectUrl} alt={mediaViewer.filename} />
            )}
            <button
              type="button"
              className="image-viewer__close"
              onClick={() => {
                URL.revokeObjectURL(mediaViewer.objectUrl);
                setMediaViewer(null);
              }}
              aria-label="Đóng"
            >
              <FiX />
            </button>
          </div>,
          document.body,
        )}
    </>
  );
}

export default MessageAttachments;
