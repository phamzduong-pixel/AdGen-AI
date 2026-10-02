const DRAFT_FIELDS = [
  "title",
  "content",
  "cta",
  "hashtags",
  "internal_notes",
  "platform",
  "platform_name",
  "status",
  "brand_id",
  "campaign_id",
  "is_campaign_primary",
];

export const normalizeEditorDraft = (source = {}) =>
  Object.fromEntries(
    DRAFT_FIELDS.map((field) => [
      field,
      source[field] ?? (
        field === "status"
          ? "draft"
          : field === "is_campaign_primary"
            ? false
            : ""
      ),
    ]),
  );

export const editorDraftEquals = (left, right) =>
  JSON.stringify(normalizeEditorDraft(left)) ===
  JSON.stringify(normalizeEditorDraft(right));

export const editorDraftKey = (contentId) => `content-editor-draft-${contentId}`;

export const parseLocalEditorDraft = (value) => {
  try {
    const parsed = JSON.parse(value);
    if (!parsed?.savedAt || !parsed?.draft?.content) return null;
    return {
      savedAt: parsed.savedAt,
      draft: normalizeEditorDraft(parsed.draft),
    };
  } catch {
    return null;
  }
};

export const buildLineDiff = (oldText = "", newText = "") => {
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");
  const length = Math.max(oldLines.length, newLines.length);
  return Array.from({ length }, (_, index) => {
    const before = oldLines[index] ?? "";
    const after = newLines[index] ?? "";
    return {
      index: index + 1,
      before,
      after,
      changed: before !== after,
      kind: !before ? "added" : !after ? "removed" : before !== after ? "changed" : "same",
    };
  });
};

const safeFilename = (title) =>
  (title || "noi-dung")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60) || "noi-dung";

export const buildEditorMarkdown = (item) =>
  [
    `# ${item.title || "Nội dung quảng cáo"}`,
    item.content || "",
    item.cta ? `## CTA\n\n${item.cta}` : "",
    item.hashtags ? `## Hashtag\n\n${item.hashtags}` : "",
  ].filter(Boolean).join("\n\n");

const downloadText = (body, filename, type) => {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

export const exportEditorContent = async (format, item, versionNumber) => {
  const markdown = buildEditorMarkdown(item);
  const date = new Date().toISOString().slice(0, 10);
  const filename = `${safeFilename(item.title)}-v${versionNumber}-${date}`;
  if (format === "copy") {
    await navigator.clipboard.writeText(markdown);
    return;
  }
  if (format === "markdown") {
    downloadText(markdown, `${filename}.md`, "text/markdown;charset=utf-8");
    return;
  }
  if (format === "txt") {
    downloadText(
      markdown.replace(/^#{1,6}\s/gm, ""),
      `${filename}.txt`,
      "text/plain;charset=utf-8",
    );
    return;
  }
  const printWindow = window.open("", "_blank", "noopener,noreferrer");
  if (!printWindow) throw new Error("Trình duyệt đã chặn cửa sổ xuất PDF.");
  const escaped = markdown
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  printWindow.document.write(
    `<title>${filename}</title><style>body{font-family:Arial,sans-serif;max-width:820px;margin:40px auto;line-height:1.65;color:#172033;white-space:pre-wrap}h1{color:#4f46e5}</style><body>${escaped}</body>`,
  );
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
};
