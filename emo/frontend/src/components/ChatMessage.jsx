import React from "react";
import EmoEyes from "./EmoEyes";
import ToolCallCard from "./ToolCallCard";

const MOOD_LABELS = {
  neutre: "Neutre",
  amusee: "Amusée",
  concentree: "Concentrée",
  sarcastique: "Sarcastique",
  enthousiaste: "Enthousiaste",
  agacee: "Agacée",
  curieuse: "Curieuse",
  pensive: "Pensive",
};

/** Render simple markdown-ish content: code blocks and inline code. */
const RichContent = ({ text }) => {
  if (!text) return null;
  const parts = text.split(/(```[\s\S]*?```)/g);
  return (
    <div className="space-y-3">
      {parts.map((part, i) => {
        if (part.startsWith("```")) {
          const inner = part.replace(/^```(\w*)\n?/, "").replace(/```$/, "");
          const lang = part.match(/^```(\w+)/)?.[1] || "";
          return (
            <pre
              key={i}
              className="font-code text-xs overflow-x-auto rounded-xl p-4 my-2"
              style={{
                background: "var(--emo-code-bg)",
                border: "1px solid rgba(255,255,255,0.06)",
                boxShadow: "inset 0 0 24px rgba(0,0,0,0.4)",
              }}
            >
              {lang && (
                <div className="text-[10px] uppercase tracking-[0.2em] text-muted-em mb-2">{lang}</div>
              )}
              <code style={{ color: "#E9D5FF" }}>{inner}</code>
            </pre>
          );
        }
        // Inline transformations
        const segments = part.split(/(`[^`]+`)/g);
        return (
          <p key={i} className="leading-relaxed whitespace-pre-wrap">
            {segments.map((seg, j) => {
              if (seg.startsWith("`") && seg.endsWith("`")) {
                return (
                  <code
                    key={j}
                    className="font-code text-[0.9em] px-1.5 py-0.5 rounded"
                    style={{ background: "rgba(168,85,247,0.12)", color: "#E9D5FF" }}
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

export const ChatMessage = ({ message, isStreaming }) => {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div data-testid="chat-message-user" className="flex justify-end animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div
          className="max-w-[80%] px-4 py-3 rounded-2xl rounded-tr-sm text-sm"
          style={{
            background: "rgba(147, 51, 234, 0.18)",
            border: "1px solid rgba(168, 85, 247, 0.22)",
            color: "var(--emo-text)",
          }}
        >
          <RichContent text={message.content} />
        </div>
      </div>
    );
  }

  const mood = message.mood;
  return (
    <div
      data-testid="chat-message-emo"
      className={`flex gap-4 max-w-[92%] mr-auto animate-in fade-in slide-in-from-bottom-2 duration-300 mode-${message.mode || "tech"}`}
    >
      <div className="flex-shrink-0 mt-1">
        <EmoEyes mode={message.mode || "tech"} mood={mood} thinking={isStreaming} size={56} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-heading text-sm font-medium" style={{ color: "var(--mode-color)" }}>
            Émo
          </span>
          {mood && (
            <span
              data-testid="mood-badge"
              className="text-[10px] uppercase tracking-[0.18em] px-2 py-0.5 rounded-full"
              style={{ background: "rgba(255,255,255,0.04)", color: "var(--emo-text-muted)" }}
            >
              {MOOD_LABELS[mood] || mood}
            </span>
          )}
          {message.verified === "true" && (
            <span
              data-testid="verified-badge"
              className="text-[10px] uppercase tracking-[0.18em] px-2 py-0.5 rounded-full flex items-center gap-1"
              style={{ background: "rgba(52,211,153,0.12)", color: "#34d399", border: "1px solid rgba(52,211,153,0.25)" }}
              title="Émo a vérifié avec ses outils"
            >
              Vérifié
            </span>
          )}
          {message.verified === "partial" && (
            <span
              data-testid="partial-badge"
              className="text-[10px] uppercase tracking-[0.18em] px-2 py-0.5 rounded-full"
              style={{ background: "rgba(245,158,11,0.12)", color: "#fbbf24" }}
              title="Vérification partielle"
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
          <div className="mb-2">
            {(message.tool_calls_live || message.tool_calls).map((t, i) => (
              <ToolCallCard
                key={t.id || i}
                event={t.id ? t : {
                  id: `hist-${i}`,
                  tool: t.name,
                  args: t.arguments,
                  state: "done",
                  result: { ok: true, summary: t.result_summary },
                }}
              />
            ))}
          </div>
        )}
        <div className="text-[15px]" style={{ color: "var(--emo-text)" }}>
          <RichContent text={message.content} />
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
