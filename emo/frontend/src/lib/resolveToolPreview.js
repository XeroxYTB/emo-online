import { isImagePath, previewTextSnippet } from "../components/SquarePreviewFrame";
import { htmlPreviewUrl, isHtmlPath } from "./filePreview";

function hasValidScreenshot(data) {
  const b64 = data?.screenshot_base64;
  if (!b64 || typeof b64 !== "string") return false;
  if (b64.includes("truncated") || b64.includes("[screenshot:")) return false;
  return b64.length > 500;
}

/** Détecte si un événement tool peut afficher un aperçu visuel. */
export function hasToolPreview(event) {
  return Boolean(resolveToolPreview(event));
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
    if (p.url) {
      return {
        kind: "interactive",
        url: p.url,
        title: p.title || p.url,
        previewText: p.preview,
        screenshot_base64: hasValidScreenshot(p) ? p.screenshot_base64 : null,
        elements: p.elements || [],
        session_id: p.session_id || "default",
      };
    }
  }

  if (preview?.type === "file") {
    return resolveFilePreview(preview.path, preview.preview, preview.is_image);
  }

  if (!result || result.ok === false) {
    const url = args.url;
    if (url && ["browser_visit", "browser_open", "web_fetch"].includes(tool)) {
      return {
        kind: "interactive",
        url,
        title: url,
        elements: [],
        session_id: "default",
      };
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
    if (path && content) return resolveFilePreview(path, content);
  }

  if (tool === "web_fetch" || tool === "browser_visit" || tool === "browser_open") {
    const url = result.url || args.url;
    if (url) {
      return {
        kind: "interactive",
        url,
        title: result.title || url,
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
  if (isHtmlPath(path)) {
    return {
      kind: "html",
      htmlUrl: htmlPreviewUrl(content),
      title: path.split(/[/\\]/).pop(),
      path,
    };
  }
  if (content.length > 20) {
    return {
      kind: "text",
      text: previewTextSnippet(content, 1200),
      title: path.split(/[/\\]/).pop(),
      path,
    };
  }
  return null;
}
