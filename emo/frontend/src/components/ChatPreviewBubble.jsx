import React from "react";
import { Globe, FileCode2 } from "lucide-react";
import SquarePreviewFrame from "./SquarePreviewFrame";
import SearchResultPreview from "./SearchResultPreview";
import InteractiveBrowser from "./InteractiveBrowser";
import { resolveToolPreview } from "../lib/resolveToolPreview";

/** Bulle d'aperçu dans le chat — navigateur interactif inline pour les sites web. */
export default function ChatPreviewBubble({ event, className = "" }) {
  const data = resolveToolPreview(event);
  if (!data) return null;

  const isBrowser = data.kind === "interactive";

  return (
    <div
      className={`rounded-2xl overflow-hidden ${className}`}
      data-testid="chat-preview-bubble"
      style={{
        background: "var(--emo-surface)",
        border: "1px solid var(--emo-border)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
      }}
    >
      <div
        className="flex items-center gap-2 px-3 py-1.5 text-[10px] uppercase tracking-wider em-border-b"
        style={{ color: "var(--emo-text-muted)" }}
      >
        {data.kind === "html" ? <FileCode2 size={11} /> : <Globe size={11} />}
        <span className="truncate flex-1 normal-case tracking-normal text-xs" style={{ color: "var(--emo-text)" }}>
          {isBrowser ? "Navigateur" : data.title || data.url || "Aperçu"}
          {isBrowser && data.title ? ` — ${data.title}` : ""}
        </span>
      </div>

      <div className="p-2">
        {data.kind === "search" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {(data.results || []).map((r, i) => (
              <SearchResultPreview
                key={r.url || i}
                url={r.url}
                title={r.title}
                subtitle={r.domain || r.url}
                snippet={r.snippet}
                testId={`bubble-search-${i}`}
              />
            ))}
          </div>
        )}

        {data.kind === "interactive" && (
          <InteractiveBrowser
            autoOpen
            compact={false}
            frame={{
              url: data.url,
              title: data.title,
              preview: data.previewText,
              screenshot_base64: data.screenshot_base64,
              elements: data.elements,
              session_id: data.session_id,
            }}
            sessionId={data.session_id}
          />
        )}

        {data.kind === "html" && (
          <SquarePreviewFrame
            kind="iframe"
            url={data.htmlUrl}
            title={data.title}
            subtitle={data.path}
            testId="bubble-html-preview"
            className="max-w-none w-full"
          />
        )}

        {data.kind === "image" && (
          <SquarePreviewFrame
            kind="image"
            src={data.src}
            title={data.title}
            subtitle={data.path}
            testId="bubble-image-preview"
            className="max-w-none"
          />
        )}

        {data.kind === "text" && (
          <SquarePreviewFrame
            kind="text"
            text={data.text}
            title={data.title}
            subtitle={data.path}
            testId="bubble-text-preview"
            className="max-w-none"
          />
        )}
      </div>
    </div>
  );
}
