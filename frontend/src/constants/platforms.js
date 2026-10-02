export const PLATFORM_OPTIONS = [
  { value: "facebook", label: "Facebook", primary: true },
  { value: "tiktok", label: "TikTok", primary: true },
  { value: "shopee", label: "Shopee", primary: true },
  { value: "instagram", label: "Instagram", extra: true },
  { value: "google_ads", label: "Google Ads", extra: true },
  { value: "other", label: "Khác", extra: true },
];

export const PRIMARY_PLATFORM_OPTIONS = PLATFORM_OPTIONS.filter(
  (platform) => platform.primary,
);

export const EXTRA_PLATFORM_OPTIONS = PLATFORM_OPTIONS.filter(
  (platform) => platform.extra,
);

export const PLATFORM_LABELS = Object.fromEntries(
  PLATFORM_OPTIONS.map(({ value, label }) => [value, label]),
);

export const LEGACY_PLATFORM_LABELS = {
  youtube: "YouTube",
  email: "Email Marketing",
  landing_page: "Landing Page",
  seo: "SEO",
  slogan: "Slogan",
  rewrite: "Viết lại",
  summarize: "Tóm tắt",
};

export const getPlatformLabel = (platform, customName = "") => {
  if (platform === "other") return customName || PLATFORM_LABELS.other;
  return PLATFORM_LABELS[platform] || LEGACY_PLATFORM_LABELS[platform] || platform || "Nội dung chung";
};

export const isCurrentPlatform = (platform) =>
  PLATFORM_OPTIONS.some((item) => item.value === platform);
