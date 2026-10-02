import { FiSearch, FiX } from "react-icons/fi";
import "./ConversationSearch.css";

function ConversationSearch({ value, onChange }) {
  return (
    <div className="conversation-search">
      <FiSearch />
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Tìm kiếm cuộc trò chuyện"
        aria-label="Tìm kiếm cuộc trò chuyện"
      />
      {value && (
        <button type="button" onClick={() => onChange("")} aria-label="Xóa tìm kiếm">
          <FiX />
        </button>
      )}
    </div>
  );
}

export default ConversationSearch;
