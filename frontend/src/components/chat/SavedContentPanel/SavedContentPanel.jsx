import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { FiBookmark, FiCopy, FiSearch, FiX } from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import useToast from "../../ui/Toast/useToast";
import SavedContentCard from "./SavedContentCard";
import { recordContentActivity } from "../../../services/api/savedContentApi";
import "./SavedContentPanel.css";

function SavedContentPanel({
  open,
  items,
  isLoading,
  pendingMessageIds,
  onClose,
  onDelete,
  onEdit,
}) {
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [selectedItem, setSelectedItem] = useState(null);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event) => {
      if (event.key !== "Escape") return;
      if (selectedItem) setSelectedItem(null);
      else onClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose, selectedItem]);

  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("vi");
    if (!normalizedQuery) return items;
    return items.filter((item) =>
      `${item.title} ${item.content}`
        .toLocaleLowerCase("vi")
        .includes(normalizedQuery),
    );
  }, [items, query]);

  const copyContent = async (item) => {
    try {
      await navigator.clipboard.writeText(item.content);
      toast.success("Đã sao chép nội dung.");
      recordContentActivity(item.id, "copy").catch(() => {});
    } catch {
      toast.error("Không thể sao chép. Hãy kiểm tra quyền clipboard.");
    }
  };

  if (!open) return null;

  return createPortal(
    <div className="saved-content-panel" role="dialog" aria-modal="true">
      <button
        type="button"
        className="saved-content-panel__backdrop"
        onClick={onClose}
        aria-label="Đóng Thư viện nội dung"
      />

      <aside className="saved-content-panel__drawer">
        <header className="saved-content-panel__header">
          <span><FiBookmark /></span>
          <div>
            <h2>Thư viện nội dung</h2>
            <p>{items.length} nội dung đã lưu</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Đóng">
            <FiX />
          </button>
        </header>

        <label className="saved-content-panel__search">
          <FiSearch />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm theo tiêu đề hoặc nội dung..."
            autoFocus
          />
        </label>

        <div className="saved-content-panel__list">
          {isLoading ? (
            <p className="saved-content-panel__empty">Đang tải thư viện...</p>
          ) : filteredItems.length ? (
            filteredItems.map((item) => (
              <SavedContentCard
                key={item.id}
                item={item}
                deleting={pendingMessageIds.has(
                  item.message_id ?? `saved-${item.id}`,
                )}
                onView={setSelectedItem}
                onCopy={copyContent}
                onDelete={onDelete}
                onEdit={onEdit}
              />
            ))
          ) : (
            <div className="saved-content-panel__empty">
              <FiBookmark />
              <strong>
                {query ? "Không tìm thấy nội dung" : "Chưa có nội dung đã lưu"}
              </strong>
              <span>
                {query
                  ? "Thử tìm bằng từ khóa khác."
                  : "Bấm Lưu dưới một phản hồi AI để thêm vào thư viện."}
              </span>
            </div>
          )}
        </div>
      </aside>

      {selectedItem && (
        <div className="saved-content-detail" role="dialog" aria-modal="true">
          <button
            type="button"
            className="saved-content-detail__backdrop"
            onClick={() => setSelectedItem(null)}
            aria-label="Đóng chi tiết"
          />
          <article className="saved-content-detail__content">
            <header>
              <div>
                <span>Nội dung đã lưu</span>
                <h2>{selectedItem.title}</h2>
              </div>
              <button
                type="button"
                onClick={() => setSelectedItem(null)}
                aria-label="Đóng"
              >
                <FiX />
              </button>
            </header>
            <div className="saved-content-detail__markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {selectedItem.content}
              </ReactMarkdown>
            </div>
            <footer>
              <button
                type="button"
                onClick={() => copyContent(selectedItem)}
              >
                <FiCopy />
                Sao chép nội dung
              </button>
            </footer>
          </article>
        </div>
      )}
    </div>,
    document.body,
  );
}

export default SavedContentPanel;
