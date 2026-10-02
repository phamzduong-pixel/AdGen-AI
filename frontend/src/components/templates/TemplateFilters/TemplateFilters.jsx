import { FiSearch } from "react-icons/fi";

import { getPlatformLabel } from "../../../constants/platforms";

import "./TemplateFilters.css";

const SCOPES = [
  ["all", "Tất cả"],
  ["popular", "Phổ biến"],
  ["favorites", "Yêu thích"],
  ["custom", "Của tôi"],
];

function TemplateFilters({
  query,
  platform,
  category,
  scope,
  platforms,
  categories,
  onChange,
}) {
  return (
    <section className="template-filters">
      <div className="template-filters__scopes">
        {SCOPES.map(([value, label]) => (
          <button
            type="button"
            key={value}
            className={scope === value ? "is-active" : ""}
            onClick={() => onChange("scope", value)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="template-filters__controls">
        <label className="template-filters__search">
          <FiSearch />
          <input
            type="search"
            value={query}
            onChange={(event) => onChange("query", event.target.value)}
            placeholder="Tìm theo tên hoặc mô tả..."
          />
        </label>
        <select
          value={platform}
          onChange={(event) => onChange("platform", event.target.value)}
          aria-label="Lọc theo nền tảng"
        >
          <option value="">Tất cả nền tảng</option>
          {platforms.map((item) => (
            <option value={item} key={item}>
              {getPlatformLabel(item)}
            </option>
          ))}
        </select>
        <select
          value={category}
          onChange={(event) => onChange("category", event.target.value)}
          aria-label="Lọc theo danh mục"
        >
          <option value="">Tất cả danh mục</option>
          {categories.map((item) => (
            <option value={item} key={item}>
              {getPlatformLabel(item)}
            </option>
          ))}
        </select>
      </div>
    </section>
  );
}

export default TemplateFilters;
