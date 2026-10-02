export const parseBrandList = (value) =>
  [
    ...new Set(
      String(value || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ];

export const validateBrandProfile = (form) => {
  const errors = {};
  if (!form.name?.trim()) errors.name = "Tên thương hiệu là bắt buộc.";
  if (form.website && !/^https?:\/\/.+/i.test(form.website)) {
    errors.website = "Website phải bắt đầu bằng http:// hoặc https://.";
  }
  for (const field of ["primary_color", "secondary_color"]) {
    if (form[field] && !/^#[0-9a-f]{6}$/i.test(form[field])) {
      errors[field] = "Màu phải có dạng HEX, ví dụ #4F46E5.";
    }
  }
  return errors;
};
