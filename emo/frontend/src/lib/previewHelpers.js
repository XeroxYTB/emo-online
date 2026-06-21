/** Helpers partagés (évite import circulaire resolveToolPreview ↔ SquarePreviewFrame). */

export function isImagePath(path = "") {
  const ext = path.split(".").pop()?.toLowerCase() || "";
  return ["png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "ico"].includes(ext);
}

export function previewTextSnippet(content = "", max = 900) {
  const t = (content || "").replace(/\r\n/g, "\n").trim();
  if (!t) return "";
  return t.length > max ? `${t.slice(0, max)}…` : t;
}
