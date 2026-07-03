import { isImagePath, previewTextSnippet } from "./previewHelpers";
import { htmlPreviewUrl, isHtmlPath } from "./filePreview";
import {
  base64ToDataUrl,
  isUsableImageBase64,
  mergeImageFields,
  resolveImageUrl,
} from "./imagePreview";

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

/** Build a displayable image src from SSE / tool result fields. */
export function buildImagePreviewSrc(input) {
  const fields = mergeImageFields(input);
  const dataUrl = base64ToDataUrl(fields.image_base64, fields.mime);
  if (dataUrl) return dataUrl;
  if (input?.src && typeof input.src === "string") {
    const fromDirect = resolveImageUrl(input.src);
    if (fromDirect) return fromDirect;
  }
  return resolveImageUrl(fields.image_url);
}

/** Pair display src + alternate (URL ↔ base64) for resilient previews. */
export function buildImagePreviewPair(input) {
  if (!input || typeof input !== "object") return { src: null, fallbackSrc: null };
  const fields = mergeImageFields(input);
  const dataUrl = base64ToDataUrl(fields.image_base64, fields.mime);
  const fromUrl = resolveImageUrl(fields.image_url);
  const main = dataUrl || fromUrl || buildImagePreviewSrc(input);
  if (!main) return { src: null, fallbackSrc: null };
  let fallbackSrc = null;
  if (main === dataUrl && fromUrl) fallbackSrc = fromUrl;
  else if (main === fromUrl && dataUrl) fallbackSrc = dataUrl;
  if (fallbackSrc === main) fallbackSrc = null;
  return { src: main, fallbackSrc };
}

/** True when event carries enough data to attempt image display. */
export function hasImagePayload(input) {
  if (!input || typeof input !== "object") return false;
  const fields = mergeImageFields(input);
  return Boolean(
    isUsableImageBase64(fields.image_base64)
    || resolveImageUrl(fields.image_url)
    || input.has_image,
  );
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
      event,
    );
  }

  if (preview?.type === "image" || (tool === "generate_image" && result?.ok !== false)) {
    const fields = mergeImageFields(preview, result);
    if (hasImagePayload(fields) || hasImagePayload(preview) || hasImagePayload(result)) {
      return {
        kind: "image",
        title: fields.title || args.prompt || "Image générée",
        imageFields: fields,
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
