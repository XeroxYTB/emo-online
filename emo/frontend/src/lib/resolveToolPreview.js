import { isImagePath, previewTextSnippet } from "../components/SquarePreviewFrame";
import { htmlPreviewUrl, isHtmlPath } from "./filePreview";

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
    const screenshot = p.screenshot_base64
      ? `data:image/jpeg;base64,${p.screenshot_base64}`
      : null;
    if (p.url || screenshot) {
      const hasInteractive =
        p.screenshot_base64 &&
        !String(p.screenshot_base64).includes("truncated") &&
        !String(p.screenshot_base64).includes("[screenshot:");
      if (hasInteractive || (p.elements || []).length) {
        return {
          kind: "interactive",
          url: p.url,
          title: p.title || p.url,
          previewText: p.preview,
          screenshot_base64: p.screenshot_base64,
          elements: p.elements || [],
          session_id: p.session_id || "default",
        };
      }
      return {
        kind: "url",
        url: p.url,
        title: p.title || p.url,
        previewText: p.preview,
        screenshotSrc: screenshot,
      };
    }
  }

  if (preview?.type === "file") {
    return resolveFilePreview(preview.path, preview.preview, preview.is_image);
  }

  if (!result || result.ok === false) return null;

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
        kind: "url",
        url,
        title: result.title || url,
        previewText: result.preview || result.text,
        screenshotSrc:
          result.screenshot_base64 && !String(result.screenshot_base64).includes("truncated")
            ? `data:image/jpeg;base64,${result.screenshot_base64}`
            : null,
      };
    }
  }

  if (result.screenshot_base64 && !String(result.screenshot_base64).includes("truncated")) {
    return {
      kind: "image",
      src: `data:image/jpeg;base64,${result.screenshot_base64}`,
      title: result.title || result.url || "Capture",
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
