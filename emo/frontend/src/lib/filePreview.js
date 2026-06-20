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
