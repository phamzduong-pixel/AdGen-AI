import { useMemo, useState } from "react";
import { FiBookmark, FiPlus, FiSearch } from "react-icons/fi";

import Modal from "../../ui/Modal/Modal";
import "./LibraryPickerModal.css";

function LibraryPickerModal({
  open,
  items,
  existingIds,
  pending,
  onClose,
  onAdd,
}) {
  const [query, setQuery] = useState("");
  const available = useMemo(
    () =>
      items.filter(
        (item) =>
          !existingIds.has(item.id) &&
          `${item.title} ${item.content}`
            .toLocaleLowerCase("vi")
            .includes(query.trim().toLocaleLowerCase("vi")),
      ),
    [existingIds, items, query],
  );
  return (
    <Modal open={open} title="Thêm từ Thư viện nội dung" onClose={onClose} closeDisabled={pending} size="lg">
      <label className="library-picker__search">
        <FiSearch />
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm nội dung..." />
      </label>
      <div className="library-picker__list">
        {available.length ? available.map((item) => (
          <article key={item.id}>
            <span><FiBookmark /></span>
            <div><strong>{item.title}</strong><p>{item.content}</p></div>
            <button type="button" onClick={() => onAdd(item.id)} disabled={pending}><FiPlus /> Thêm</button>
          </article>
        )) : (
          <p className="library-picker__empty">Không còn nội dung phù hợp để thêm.</p>
        )}
      </div>
    </Modal>
  );
}

export default LibraryPickerModal;
