import { getPreferences } from "./settingsStorage";

const safeFilename = (title) =>
  (title || "cuoc-tro-chuyen")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60) || "cuoc-tro-chuyen";

const buildMarkdown = (title, messages) => {
  const { includeTimestamps } = getPreferences();
  const exportedAt = new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "full",
    timeStyle: "medium",
  }).format(new Date());
  const body = messages
    .map((message) => {
      const author = message.role === "user" ? "Người dùng" : "AdGen AI";
      const time = includeTimestamps && message.time ? ` — ${message.time}` : "";
      return `## ${author}${time}\n\n${message.content}`;
    })
    .join("\n\n---\n\n");
  return `# ${title}\n\n_Xuất lúc ${exportedAt}_\n\n${body}\n`;
};

const downloadText = (content, filename, type) => {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

export const exportConversation = async (format, title, messages) => {
  const targetFormat = format || getPreferences().defaultExportFormat || "markdown";
  const markdown = buildMarkdown(title, messages);
  const filename = safeFilename(title);

  if (targetFormat === "markdown") {
    downloadText(markdown, `${filename}.md`, "text/markdown;charset=utf-8");
    return;
  }
  if (targetFormat === "txt") {
    downloadText(
      markdown.replace(/^#{1,6}\s/gm, "").replace(/^---$/gm, ""),
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
    `<title>${filename}</title><style>body{font-family:Arial,sans-serif;max-width:820px;margin:40px auto;line-height:1.6;color:#172033;white-space:pre-wrap}h1{color:#4f46e5}</style><body>${escaped}</body>`,
  );
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
};
