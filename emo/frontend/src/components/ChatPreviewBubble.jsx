import React, { useState } from "react";
import { Globe, FileCode2, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import SquarePreviewFrame from "./SquarePreviewFrame";
import SearchResultPreview from "./SearchResultPreview";
import InteractiveBrowser from "./InteractiveBrowser";
import LiveHtmlPreview from "./LiveHtmlPreview";
import { resolveToolPreview } from "../lib/resolveToolPreview";
import { normalizeFilePath } from "../lib/filePreview";

/** Bulle d'aperçu dans le chat — navigateur interactif inline pour les sites web. */
export default function ChatPreviewBubble({ event, className = "", liveHtmlByPath = {}, showCopyCode = false }) {
  const data = resolveToolPreview(event);
  const [copied, setCopied] = useState(false);
  if (!data) return null;

  const liveHtmlContent =
    data.kind === "html" && data.path
      ? liveHtmlByPath[normalizeFilePath(data.path)] ?? liveHtmlByPath[data.path] ?? data.fullContent
      : data.fullContent;

  const isBrowser = data.kind === "interactive";
  const copyContent =
    data.kind === "html" ? liveHtmlContent || data.fullContent : data.fullContent;
  const canCopy = showCopyCode && (data.kind === "text" || data.kind === "html") && copyContent;

  const handleCopy = async () => {
    if (!copyContent) return;
    try {
      await navigator.clipboard.writeText(copyContent);
      setCopied(true);
      toast.success("Code copié");
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Copie impossible");
    }
  };

  return (
    <div
      className={`rounded-2xl overflow-hidden ${className}`}
      data-testid="chat-preview-bubble"
      style={{
        background: "var(--emo-surface)",
        border: "1px solid var(--emo-border)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
      }}
    >
      <div
        className="flex items-center gap-2 px-3 py-2 em-border-b"
        style={{ background: "var(--emo-subtle-bg, var(--emo-surface))" }}
      >
        {isBrowser ? (
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: "var(--mode-color)" }}
            aria-hidden
          />
        ) : data.kind === "html" ? (
          <FileCode2 size={12} style={{ color: "var(--emo-text-muted)" }} />
        ) : (
          <Globe size={12} style={{ color: "var(--emo-text-muted)" }} />
        )}
        <span className="truncate flex-1 text-xs font-medium" style={{ color: "var(--emo-text)" }}>
          {isBrowser
            ? data.title || data.url?.replace(/^https?:\/\//, "") || "Navigateur"
            : data.title || data.url || "Aperçu"}
        </span>
        {canCopy && (
          <button
            type="button"
            data-testid="chat-copy-code-btn"
            title="Copier tout le code"
            onClick={handleCopy}
            className="flex-shrink-0 flex items-center gap-1 px-2 py-1 rounded-md text-[10px] em-hover-subtle transition"
            style={{ color: copied ? "var(--emo-success-text)" : "var(--emo-text-muted)" }}
          >
            {copied ? <Check size={11} /> : <Copy size={11} />}
            <span className="hidden sm:inline">{copied ? "Copié" : "Copier"}</span>
          </button>
        )}
      </div>

      <div className={isBrowser ? "p-2" : "p-3"}>
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
            embedded
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
          <LiveHtmlPreview
            path={data.path}
            title={data.title}
            content={liveHtmlContent || ""}
            compact={false}
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
