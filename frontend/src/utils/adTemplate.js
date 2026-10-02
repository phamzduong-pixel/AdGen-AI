const OBJECTIVE_BY_CATEGORY = {
  "Ra mắt sản phẩm": "Nhận diện thương hiệu",
  "Quảng cáo khuyến mãi": "Tăng chuyển đổi/bán hàng",
  "Thu hút khách hàng tiềm năng": "Thu hút khách hàng tiềm năng",
  "Mô tả sản phẩm": "Tăng chuyển đổi/bán hàng",
  "Nhận diện thương hiệu": "Nhận diện thương hiệu",
};

export const buildTemplateBrief = (template) => ({
  product_name: "",
  description: template.description || template.title,
  target_audience: "",
  objective:
    OBJECTIVE_BY_CATEGORY[template.category] ||
    "Tăng chuyển đổi/bán hàng",
  platform: template.platform,
  tone: template.default_tone,
  length: template.default_length,
  keywords: "",
  cta: template.suggested_cta || "",
  language: "Tiếng Việt",
});

export const filterAdTemplates = (templates, filters) => {
  const normalizedQuery = filters.query.trim().toLocaleLowerCase("vi");
  return templates.filter((template) => {
    const matchesQuery =
      !normalizedQuery ||
      `${template.title} ${template.description}`
        .toLocaleLowerCase("vi")
        .includes(normalizedQuery);
    const matchesPlatform =
      !filters.platform || template.platform === filters.platform;
    const matchesCategory =
      !filters.category || template.category === filters.category;
    const matchesScope =
      filters.scope === "all" ||
      (filters.scope === "popular" && template.is_popular) ||
      (filters.scope === "favorites" && template.is_favorite) ||
      (filters.scope === "custom" && template.is_owner);
    return (
      matchesQuery &&
      matchesPlatform &&
      matchesCategory &&
      matchesScope
    );
  });
};
