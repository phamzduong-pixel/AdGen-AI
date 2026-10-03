import { FiBriefcase, FiChevronDown } from "react-icons/fi";
import "./BrandSelector.css";

function BrandSelector({
  brands = [],
  value = null,
  onChange,
  disabled = false,
  compact = false,
}) {
  return (
    <label
      className={`brand-selector ${compact ? "brand-selector--compact" : ""}`}
      title="Chọn hồ sơ thương hiệu cho nội dung AI"
    >
      <FiBriefcase className="brand-selector__icon" aria-hidden="true" />
      <select
        value={value ?? ""}
        onChange={(event) =>
          onChange?.(event.target.value ? Number(event.target.value) : null)
        }
        disabled={disabled}
        aria-label="Hồ sơ thương hiệu"
      >
        <option value="">Không dùng thương hiệu</option>
        {brands.map((brand) => (
          <option key={brand.id} value={brand.id}>
            {brand.name}{brand.is_default ? " (mặc định)" : ""}
          </option>
        ))}
      </select>
      <FiChevronDown className="brand-selector__chevron" aria-hidden="true" />
    </label>
  );
}

export default BrandSelector;
