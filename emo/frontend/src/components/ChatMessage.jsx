import React, { useState } from "react";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";
import EmoEyes from "./EmoEyes";
import ToolCallCard from "./ToolCallCard";
import LiveHtmlPreview from "./LiveHtmlPreview";
import { cleanDisplayText } from "../lib/messageClean";
import { buildImagePreviewSrc } from "../lib/resolveToolPreview";

const MOOD_LABELS = {
  neutre: "Neutre",
  amusee: "Amusée",
  concentree: "Concentrée",
  sarcastique: "Sarcastique",
  ironique: "Ironique",
  enthousiaste: "Enthousiaste",
  agacee: "Agacée",
  curieuse: "Curieuse",
  pensive: "Pensive",
};

const RichContent = ({ text, images, showCopyCode = false }) => {
  if (images?.length) {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {images.map((img, i) => (
            <img
              key={i}
              src={img.startsWith("data:") ? img : `data:image/jpeg;base64,${img}`}
              alt=""
              className="max-h-52 rounded-xl em-border object-contain"
              style={{ boxShadow: "var(--emo-shadow-sm)" }}
            />
          ))}
        </div>
        {text ? <RichText text={text} showCopyCode={showCopyCode} /> : null}
      </div>
    );
  }
  return <RichText text={text} showCopyCode={showCopyCode} />;
};

const CodeBlock = ({ inner, lang, showCopyCode }) => {
  const [copied, setCopied] = useState(false);
  const isHtml = ["html", "htm"].includes((lang || "").toLowerCase());

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(inner);
      setCopied(true);
      toast.success("Code copié");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Impossible de copier");
    }
  };

  return (
    <div className="space-y-2">
      <div className="relative">
        {showCopyCode && (
          <button
            type="button"
            data-testid="markdown-copy-code-btn"
            onClick={handleCopy}
            className="absolute top-2.5 right-2.5 flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] em-hover-subtle z-10"
            style={{ color: copied ? "var(--emo-success-text)" : "var(--emo-text-muted)" }}
            title="Copier tout le code"
          >
            {copied ? <Check size={11} /> : <Copy size={11} />}
            <span className="hidden sm:inline">{copied ? "Copié" : "Copier"}</span>
          </button>
        )}
        <pre
          className="font-code text-xs overflow-x-auto rounded-xl p-4 my-2"
          style={{
            background: "var(--emo-code-bg)",
            border: "1px solid var(--emo-border)",
            boxShadow: "var(--emo-code-inset)",
          }}
        >
          {lang && (
            <div className="text-[10px] uppercase tracking-[0.15em] text-muted-em mb-2">{lang}</div>
          )}
          <code style={{ color: "var(--emo-code-text)" }}>{inner}</code>
        </pre>
      </div>
      {showCopyCode && isHtml && inner.trim() && (
        <LiveHtmlPreview path="page.html" title="Aperçu HTML" content={inner} compact={false} />
      )}
    </div>
  );
};

const RichText = ({ text, showCopyCode = false }) => {
  if (!text) return null;
  const parts = text.split(/(```[\s\S]*?```|!\[[^\]]*\]\([^)]+\))/g);
  return (
    <div className="space-y-3">
      {parts.map((part, i) => {
        if (part.startsWith("```")) {
          const inner = part.replace(/^```(\w*)\n?/, "").replace(/```$/, "");
          const lang = part.match(/^```(\w+)/)?.[1] || "";
          return (
            <CodeBlock key={i} inner={inner} lang={lang} showCopyCode={showCopyCode} />
          );
        }
        const imgMatch = part.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
        if (imgMatch) {
          const [, alt, src] = imgMatch;
          const resolved = src.startsWith("data:") || src.startsWith("http")
            ? src
            : `data:image/jpeg;base64,${src}`;
          return (
            <img
              key={i}
              src={resolved}
              alt={alt || ""}
              className="max-w-full rounded-xl em-border my-2"
              style={{ maxHeight: 420, objectFit: "contain", boxShadow: "var(--emo-shadow-sm)" }}
            />
          );
        }
        const segments = part.split(/(`[^`]+`)/g);
        return (
          <p key={i} className="leading-relaxed whitespace-pre-wrap">
            {segments.map((seg, j) => {
              if (seg.startsWith("`") && seg.endsWith("`")) {
                return (
                  <code
                    key={j}
                    className="font-code text-[0.88em] px-1.5 py-0.5 rounded-md"
                    style={{ background: "var(--emo-inline-code-bg)", color: "var(--emo-inline-code-text)" }}
                  >
                    {seg.slice(1, -1)}
                  </code>
                );
              }
              return <span key={j}>{seg}</span>;
            })}
          </p>
        );
      })}
    </div>
  );
};

function normalizeToolEvent(t, i) {
  if (t.tool && t.state && (t.args || t.arguments)) return t;
  const args = t.arguments || t.args || {};
  const tool = t.name || t.tool;
  const result = {
    ok: true,
    path: args.path,
    url: args.url,
    content: args.content,
    title: args.title,
  };
  let inlinePreview = t.inlinePreview || null;
  if (!inlinePreview && tool === "web_search" && t.result?.results?.length) {
    inlinePreview = {
      type: "browser",
      action: "search",
      query: t.result.query || args.query || "",
      results: (t.result.results || []).slice(0, 8),
    };
  }
  if (
    !inlinePreview &&
    ["browser_visit", "browser_open", "web_fetch", "browser_click", "browser_snapshot", "browser_scroll", "browser_press", "browser_type", "browser_fill"].includes(tool) &&
    (t.result?.url || args.url || t.result?.screenshot_base64)
  ) {
    inlinePreview = {
      type: "browser",
      action: tool === "browser_open" ? "control" : "visit",
      url: t.result?.url || args.url,
      title: t.result?.title,
      preview: t.result?.preview || t.result?.text,
      screenshot_base64: t.result?.screenshot_base64,
      elements: t.result?.elements || [],
      session_id: t.result?.session_id || "default",
    };
  }
  if (!inlinePreview && tool === "edit_file" && args.path && t.result?.content) {
    inlinePreview = {
      type: "file",
      path: args.path,
      preview: String(t.result.content).slice(0, 50000),
      language: (args.path.split(".").pop() || "").toLowerCase(),
    };
  }
  if (!inlinePreview && tool === "write_file" && args.path && args.content) {
    inlinePreview = {
      type: "file",
      path: args.path,
      preview: String(args.content).slice(0, 50000),
      language: (args.path.split(".").pop() || "").toLowerCase(),
    };
  }
  if (!inlinePreview && tool === "generate_image") {
    const res = t.result;
    if (res?.ok !== false) {
      const src = buildImagePreviewSrc(res);
      if (src) {
        inlinePreview = {
          type: "image",
          src,
          title: args.prompt || res.prompt || res.subject || "Image générée",
        };
      }
    }
  }
  return {
    id: t.id || `hist-${i}`,
    tool,
    args,
    state: t.state || "done",
    result: t.result || result,
    inlinePreview,
  };
}

export const ChatMessage = ({ message, isStreaming, liveHtmlByPath = {}, showCopyCode = false }) => {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div data-testid="chat-message-user" className="flex justify-end emo-msg-animate">
        <div className="emo-bubble-user">
          <RichContent text={cleanDisplayText(message.content)} images={message.images} showCopyCode={showCopyCode} />
        </div>
      </div>
    );
  }

  const mood = message.mood;
  return (
    <div
      data-testid="chat-message-emo"
      className={`flex gap-3 max-w-full emo-msg-animate mode-${message.mode || "tech"}`}
    >
      <div className="flex-shrink-0 mt-0.5">
        <EmoEyes mode={message.mode || "tech"} mood={mood} thinking={isStreaming} size={44} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <span className="font-heading text-sm font-semibold" style={{ color: "var(--mode-color)" }}>
            Émo
          </span>
          {mood && mood !== "neutre" && (
            <span
              data-testid="mood-badge"
              className="text-[10px] px-2 py-0.5 rounded-full"
              style={{ background: "var(--emo-badge-bg)", color: "var(--emo-text-muted)" }}
            >
              {MOOD_LABELS[mood] || mood}
            </span>
          )}
          {message.verified === "true" && (
            <span
              data-testid="verified-badge"
              className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full emo-alert-success"
              title="Vérifié"
            >
              Vérifié
            </span>
          )}
          {message.verified === "partial" && (
            <span
              data-testid="partial-badge"
              className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full emo-alert-warning"
              title="Partiel"
            >
              Partiel
            </span>
          )}
          {isStreaming && (
            <span className="dot-loading">
              <span></span><span></span><span></span>
            </span>
          )}
        </div>

        {((message.tool_calls_live && message.tool_calls_live.length > 0) ||
          (message.tool_calls && message.tool_calls.length > 0)) && (
          <div className="mb-3 space-y-2">
            {(message.tool_calls_live || message.tool_calls).map((t, i) => (
              <ToolCallCard
                key={t.id || i}
                event={normalizeToolEvent(t, i)}
                liveHtmlByPath={liveHtmlByPath}
                showCopyCode={showCopyCode}
              />
            ))}
          </div>
        )}

        {(message.content || message.images?.length) && (
          <div className="emo-bubble-assistant" style={{ color: "var(--emo-text)" }}>
            <RichContent text={cleanDisplayText(message.content)} images={message.images} showCopyCode={showCopyCode} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
