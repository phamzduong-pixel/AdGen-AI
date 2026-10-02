import { useMemo, useState } from "react";
import { FiBookmark, FiSearch } from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import SavedContentCard from "../../components/chat/SavedContentPanel/SavedContentCard";
import Modal from "../../components/ui/Modal/Modal";
import useToast from "../../components/ui/Toast/useToast";
import useSavedContents from "../../hooks/useSavedContents";
import WorkspaceLayout from "../../layouts/WorkspaceLayout";
import { useNavigate } from "react-router-dom";
import { createContentDocument } from "../../services/api/contentEditorApi";
import { getUserErrorMessage } from "../../utils/apiError";
import { recordContentActivity } from "../../services/api/savedContentApi";
import "./Library.css";

function Library() {
  const navigate = useNavigate();
  const toast = useToast();
  const {
    savedContents,
    pendingMessageIds,
    isLoading,
    deleteSavedContent,
  } = useSavedContents();
  const [query, setQuery] = useState("");
  const [selectedItem, setSelectedItem] = useState(null);
  const filtered = useMemo(
    () =>
      savedContents.filter((item) =>
        `${item.title} ${item.content}`
          .toLocaleLowerCase("vi")
          .includes(query.trim().toLocaleLowerCase("vi")),
      ),
    [query, savedContents],
  );

  const copy = async (item) => {
    try {
      await navigator.clipboard.writeText(item.content);
      toast.success("Đã sao chép nội dung.");
      recordContentActivity(item.id, "copy").catch(() => {});
    } catch {
      toast.error("Không thể sao chép nội dung.");
    }
  };

  const edit = async (item) => {
    try {
      const document = await createContentDocument({
        source_saved_content_id: item.id,
      });
      navigate(`/contents/${document.id}`);
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể mở trình soạn thảo."));
    }
  };

  return (
    <WorkspaceLayout
      title="Thư viện nội dung"
      subtitle={`${savedContents.length} nội dung quảng cáo đã lưu`}
    >
      <label className="library-page__search">
        <FiSearch />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Tìm theo tiêu đề hoặc nội dung..."
        />
      </label>
      {isLoading ? (
        <div className="library-page__loading">Đang tải Thư viện nội dung...</div>
      ) : filtered.length ? (
        <div className="library-page__grid">
          {filtered.map((item) => (
            <SavedContentCard
              key={item.id}
              item={item}
              deleting={pendingMessageIds.has(item.message_id ?? `saved-${item.id}`)}
              onView={setSelectedItem}
              onCopy={() => copy(item)}
              onDelete={deleteSavedContent}
              onEdit={edit}
            />
          ))}
        </div>
      ) : (
        <div className="library-page__empty">
          <FiBookmark />
          <h2>{query ? "Không tìm thấy nội dung" : "Thư viện đang trống"}</h2>
          <p>Lưu một phản hồi AI hoặc phiên bản A/B để xem tại đây.</p>
        </div>
      )}
      <Modal open={Boolean(selectedItem)} title={selectedItem?.title} onClose={() => setSelectedItem(null)} size="lg">
        <div className="library-page__markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedItem?.content || ""}</ReactMarkdown>
        </div>
      </Modal>
    </WorkspaceLayout>
  );
}

export default Library;
