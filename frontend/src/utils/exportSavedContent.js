const safeFilename = (title) =>
  (title || "noi-dung-quang-cao")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60) || "noi-dung-quang-cao";

export const exportSavedContent = (item) => {
  const body = `# ${item.title}\n\n${item.content}\n`;
  const url = URL.createObjectURL(
    new Blob([body], { type: "text/markdown;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `${safeFilename(item.title)}.md`;
  link.click();
  URL.revokeObjectURL(url);
};
