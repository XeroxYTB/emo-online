export function fileExt(path = "") {
  return (path.split(/[/\\]/).pop() || "").split(".").pop()?.toLowerCase() || "";
}

export function isHtmlPath(path = "") {
  return ["html", "htm"].includes(fileExt(path));
}

export function htmlPreviewUrl(content = "") {
  return `data:text/html;charset=utf-8,${encodeURIComponent(content.slice(0, 500000))}`;
}

export function parentDir(path = "") {
  const normalized = path.replace(/[/\\]+$/, "");
  const idx = Math.max(normalized.lastIndexOf("/"), normalized.lastIndexOf("\\"));
  if (idx <= 0) {
    if (/^[A-Za-z]:/.test(normalized)) return normalized.slice(0, 2) + "\\";
    return normalized.startsWith("/") ? "/" : "~";
  }
  return normalized.slice(0, idx);
}

export function basename(path = "") {
  return path.split(/[/\\]/).pop() || path;
}

export function normalizeFilePath(path = "") {
  return String(path).replace(/\\/g, "/").toLowerCase();
}

const FILE_TOOLS = new Set(["write_file", "read_file", "edit_file"]);

/** Contenu complet d'un fichier généré/affiché dans le chat (aperçus live inclus). */
export function getFileContentFromToolEvent(event, liveHtmlByPath = {}) {
  if (!event) return "";
  const tool = event.tool;
  const args = event.args || {};
  const preview = event.inlinePreview;
  const result = event.result || {};
  const path = preview?.path || result.path || args.path || "";
  const normPath = path ? normalizeFilePath(path) : "";

  if (path && liveHtmlByPath?.[path]) return String(liveHtmlByPath[path]);
  if (normPath && liveHtmlByPath?.[normPath]) return String(liveHtmlByPath[normPath]);

  if (preview?.type === "file" && preview.preview != null) {
    return String(preview.preview);
  }

  if (tool === "write_file") return String(args.content ?? result.content ?? "");
  if (tool === "edit_file") return String(result.content ?? args.content ?? "");
  if (tool === "read_file") return String(result.content ?? "");

  return "";
}

export function isCopyableFileToolEvent(event) {
  if (!event) return false;
  if (!FILE_TOOLS.has(event.tool)) return false;
  return Boolean(event.args?.path || event.inlinePreview?.path || event.result?.path);
}
