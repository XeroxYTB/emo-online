import { isImagePath, previewTextSnippet } from "./previewHelpers";
import { htmlPreviewUrl, isHtmlPath } from "./filePreview";
import { getApiBase } from "./api";

const BROWSER_TOOLS = [
  "web_fetch", "browser_visit", "browser_open",
  "browser_click", "browser_snapshot", "browser_scroll", "browser_press", "browser_type", "browser_fill",
];

function hasValidScreenshot(data) {
  const b64 = data?.screenshot_base64;
  if (!b64 || typeof b64 !== "string") return false;
  if (b64.includes("truncated") || b64.includes("[screenshot:")) return false;
  return b64.length > 500;
}

/** True when base64 payload is displayable (not a UI placeholder). */
function isUsableImageBase64(b64) {
  return b64 && typeof b64 === "string" && !b64.startsWith("[") && b64.length > 100;
}

/** Resolve relative API image paths to absolute URLs. */
function resolveImageUrl(url) {
  if (!url || typeof url !== "string") return null;
  if (url.startsWith("data:")) {
    if (url.includes("[image:") || url.endsWith("base64,") || url.length < 120) return null;
    return url;
  }
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  const apiBase = getApiBase().replace(/\/$/, "");
  const path = url.startsWith("/") ? url : `/${url}`;
  return `${apiBase}${path}`;
}

/** Build a displayable image src from SSE / tool result fields. */
export function buildImagePreviewSrc(input) {
  if (!input || typeof input !== "object") return null;
  const { src: directSrc, image_base64, image_url, mime = "image/png" } = input;
  const b64 = image_base64;
  if (isUsableImageBase64(b64)) {
    return `data:${mime || "image/png"};base64,${b64}`;
  }
  if (directSrc && typeof directSrc === "string") {
    const fromDirect = resolveImageUrl(directSrc);
    if (fromDirect) return fromDirect;
  }
  const fromUrl = resolveImageUrl(image_url);
  if (fromUrl) return fromUrl;
  return null;
}

/** Pair display src + alternate (URL ↔ base64) for resilient previews. */
export function buildImagePreviewPair(input) {
  if (!input || typeof input !== "object") return { src: null, fallbackSrc: null };
  const { src: rawSrc, image_base64, image_url, mime = "image/png" } = input;
  const dataUrl = isUsableImageBase64(image_base64)
    ? `data:${mime || "image/png"};base64,${image_base64}`
    : null;
  const fromUrl = resolveImageUrl(image_url);
  // Prefer inline base64 — survives HF /generated-image 404 across workers.
  const main = dataUrl || fromUrl || buildImagePreviewSrc(input);
  if (!main) return { src: null, fallbackSrc: null };
  let fallbackSrc = null;
  if (main === dataUrl && fromUrl) {
    fallbackSrc = fromUrl;
  } else if (main === fromUrl && dataUrl) {
    fallbackSrc = dataUrl;
  } else if (rawSrc && typeof rawSrc === "string" && rawSrc.startsWith("data:") && rawSrc !== main) {
    fallbackSrc = resolveImageUrl(rawSrc);
  }
  if (fallbackSrc === main) fallbackSrc = null;
  return { src: main, fallbackSrc };
}

/** Détecte si un événement tool peut afficher un aperçu visuel. */
export function hasToolPreview(event) {
  return Boolean(resolveToolPreview(event));
}

/** Contenu fichier complet pour copie (priorité SSE > args > result). */
export function resolveFullCopyContent(event) {
  const preview = event?.inlinePreview;
  const result = event?.result;
  const args = event?.args || {};
  const tool = event?.tool;

  if (preview?.preview) return preview.preview;
  if (tool === "write_file" || tool === "edit_file") {
    if (args.content) return args.content;
  }
  if (result?.content) return result.content;
  return "";
}

function enrichWithFullContent(data, event) {
  if (!data || (data.kind !== "text" && data.kind !== "html")) return data;
  const copyContent = resolveFullCopyContent(event);
  return copyContent ? { ...data, fullContent: copyContent } : data;
}

/** Résout les données d'aperçu pour fichier, HTML, site, capture. */
export function resolveToolPreview(event) {
  const preview = event?.inlinePreview;
  const result = event?.result;
  const tool = event?.tool;
  const args = event?.args || {};

  if (preview?.type === "browser") {
    const p = preview;
    if (p.action === "search" && (p.results || []).length) {
      return {
        kind: "search",
        title: p.query || "Recherche",
        results: (p.results || []).slice(0, 4),
      };
    }
    if (p.url || hasValidScreenshot(p)) {
      return {
        kind: "interactive",
        url: p.url || result?.url || "",
        title: p.title || p.url || "Navigateur",
        previewText: p.preview,
        screenshot_base64: hasValidScreenshot(p) ? p.screenshot_base64 : null,
        elements: p.elements || [],
        session_id: p.session_id || "default",
      };
    }
  }

  if (preview?.type === "file") {
    return enrichWithFullContent(
      resolveFilePreview(preview.path, preview.preview, preview.is_image),
      event
    );
  }

  if (preview?.type === "image") {
    const { src, fallbackSrc } = buildImagePreviewPair(preview);
    if (src) {
      return {
        kind: "image",
        src,
        fallbackSrc,
        title: preview.title || "Image",
      };
    }
  }

  if (!result || result.ok === false) {
    const url = args.url;
    if (url && BROWSER_TOOLS.includes(tool)) {
      return {
        kind: "interactive",
        url,
        title: url,
        elements: [],
        session_id: "default",
      };
    }
    if (tool === "generate_image" && result?.error) {
      return { kind: "text", text: result.error, title: "Génération d'image" };
    }
    return null;
  }

  if (tool === "generate_image" && result?.ok) {
    const { src, fallbackSrc } = buildImagePreviewPair(result);
    if (src) {
      return {
        kind: "image",
        src,
        fallbackSrc,
        title: args.prompt || result.prompt || result.subject || "Image générée",
      };
    }
    if (result.has_image) return null;
  }

  if (tool === "web_search" && (result.results || []).length) {
    return {
      kind: "search",
      title: result.query || args.query || "Recherche",
      results: (result.results || []).slice(0, 4),
    };
  }

  if (tool === "write_file" || tool === "read_file" || tool === "edit_file") {
    const path = result.path || args.path || preview?.path || "";
    const content =
      tool === "write_file" || tool === "edit_file"
        ? (args.content || result.content || preview?.preview || "")
        : (result.content || preview?.preview || "");
    if (path && content) {
      return enrichWithFullContent(resolveFilePreview(path, content), event);
    }
  }

  if (BROWSER_TOOLS.includes(tool)) {
    const url = result.url || args.url;
    if (url || hasValidScreenshot(result)) {
      return {
        kind: "interactive",
        url: url || "",
        title: result.title || url || "Capture",
        previewText: result.preview || result.text,
        screenshot_base64: hasValidScreenshot(result) ? result.screenshot_base64 : null,
        elements: result.elements || [],
        session_id: result.session_id || "default",
      };
    }
  }

  if (hasValidScreenshot(result)) {
    return {
      kind: "interactive",
      url: result.url || "",
      title: result.title || result.url || "Capture",
      screenshot_base64: result.screenshot_base64,
      elements: result.elements || [],
      session_id: result.session_id || "default",
    };
  }

  return null;
}

function resolveFilePreview(path, content, isImage) {
  if (!path || !content) return null;
  if (isImage && content.startsWith("data:")) {
    return { kind: "image", src: content, title: path.split(/[/\\]/).pop(), path };
  }
  if (isImagePath(path) && content.startsWith("data:")) {
    return { kind: "image", src: content, title: path.split(/[/\\]/).pop(), path };
  }
  if (isImage && !content.startsWith("data:") && content.length > 100) {
    return {
      kind: "image",
      src: `data:image/jpeg;base64,${content}`,
      title: path.split(/[/\\]/).pop(),
      path,
    };
  }
  if (isHtmlPath(path)) {
    return {
      kind: "html",
      htmlUrl: htmlPreviewUrl(content),
      title: path.split(/[/\\]/).pop(),
      path,
      fullContent: content,
    };
  }
  if (content.length > 20) {
    return {
      kind: "text",
      text: previewTextSnippet(content, 1200),
      title: path.split(/[/\\]/).pop(),
      path,
      fullContent: content,
    };
  }
  return null;
}
