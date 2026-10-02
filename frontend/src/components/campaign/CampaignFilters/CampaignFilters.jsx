import { FiSearch } from "react-icons/fi";
import { PLATFORM_OPTIONS } from "../../../constants/platforms";

function CampaignFilters({ filters, onChange }) {
  const update = (name, value) => onChange({ ...filters, [name]: value });
  return (
    <div className="campaign-filters">
      <label>
        <FiSearch />
        <input
          type="search"
          value={filters.query}
          onChange={(event) => update("query", event.target.value)}
          placeholder="Tìm chiến dịch..."
        />
      </label>
      <select value={filters.status} onChange={(event) => update("status", event.target.value)}>
        <option value="">Mọi trạng thái</option>
        <option value="draft">Bản nháp</option>
        <option value="active">Đang chạy</option>
        <option value="completed">Hoàn thành</option>
        <option value="archived">Lưu trữ</option>
      </select>
      <select value={filters.platform} onChange={(event) => update("platform", event.target.value)}>
        <option value="">Mọi nền tảng</option>
        {PLATFORM_OPTIONS.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
      </select>
    </div>
  );
}

export default CampaignFilters;
