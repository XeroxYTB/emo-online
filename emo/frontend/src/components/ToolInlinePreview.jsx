import React from "react";
import SquarePreviewFrame, { isImagePath, previewTextSnippet } from "./SquarePreviewFrame";

/** Aperçu inline dans le chat — site, HTML, fichier, capture navigateur. */
export function ToolInlinePreview({ event }) {
  const preview = event?.inlinePreview;
  const result = event?.result;
  const tool = event?.tool;
  const args = event?.args || {};

  if (preview?.type === "browser") {
    const p = preview;
    if (p.action === "search" && (p.results || []).length) {
      const first = p.results[0];
      return (
        <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
          {(p.results || []).slice(0, 4).map((r, i) => (
            <SquarePreviewFrame
              key={r.url || i}
              kind="iframe"
              url={r.url}
              title={r.title || r.url}
              subtitle={r.url}
              testId={`inline-search-${i}`}
              className="max-w-none"
            />
          ))}
        </div>
      );
    }
    const screenshot = p.screenshot_base64
      ? `data:image/jpeg;base64,${p.screenshot_base64}`
      : null;
    if (screenshot) {
      return (
        <div className="mt-2">
          <SquarePreviewFrame kind="image" src={screenshot} title={p.title || p.url} subtitle={p.url} testId="inline-browser-shot" />
        </div>
      );
    }
    if (p.url) {
      return (
        <div className="mt-2">
          <SquarePreviewFrame kind="iframe" url={p.url} title={p.title || p.url} subtitle={p.url} testId="inline-browser-url" />
        </div>
      );
    }
  }

  if (preview?.type === "file") {
    const path = preview.path || "";
    const content = preview.preview || "";
    if (preview.is_image && content.startsWith("data:")) {
      return (
        <div className="mt-2">
          <SquarePreviewFrame kind="image" src={content} title={path} testId="inline-file-image" />
        </div>
      );
    }
    const ext = (preview.language || path.split(".").pop() || "").toLowerCase();
    if (["html", "htm"].includes(ext)) {
      return (
        <div className="mt-2">
          <SquarePreviewFrame
            kind="iframe"
            url={`data:text/html;charset=utf-8,${encodeURIComponent(content)}`}
            title={path}
            subtitle="HTML"
            testId="inline-file-html"
          />
        </div>
      );
    }
    if (content) {
      return (
        <div className="mt-2">
          <SquarePreviewFrame kind="text" text={previewTextSnippet(content, 1200)} title={path} testId="inline-file-text" />
        </div>
      );
    }
  }

  if (!result || result.ok === false) return null;

  if (tool === "web_fetch" || tool === "browser_visit" || tool === "browser_open") {
    const url = result.url || args.url;
    if (url) {
      return (
        <div className="mt-2">
          <SquarePreviewFrame kind="iframe" url={url} title={result.title || url} subtitle={url} testId="inline-tool-url" />
        </div>
      );
    }
  }

  if (tool === "read_file" && result.content) {
    const path = result.path || args.path || "";
    if (isImagePath(path)) return null;
    const ext = path.split(".").pop()?.toLowerCase() || "";
    if (["html", "htm"].includes(ext)) {
      return (
        <div className="mt-2">
          <SquarePreviewFrame
            kind="iframe"
            url={`data:text/html;charset=utf-8,${encodeURIComponent(result.content.slice(0, 50000))}`}
            title={path}
            testId="inline-read-html"
          />
        </div>
      );
    }
    if (result.content.length > 20) {
      return (
        <div className="mt-2">
          <SquarePreviewFrame kind="text" text={previewTextSnippet(result.content, 900)} title={path} testId="inline-read-text" />
        </div>
      );
    }
  }

  if (result.screenshot_base64 && !String(result.screenshot_base64).includes("truncated")) {
    return (
      <div className="mt-2">
        <SquarePreviewFrame
          kind="image"
          src={`data:image/jpeg;base64,${result.screenshot_base64}`}
          title={result.title || result.url || "Capture"}
          testId="inline-screenshot"
        />
      </div>
    );
  }

  return null;
}

export default ToolInlinePreview;
