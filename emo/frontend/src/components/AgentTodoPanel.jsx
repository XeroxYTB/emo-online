import React, { useState } from "react";
import { Brain, CheckSquare, ChevronDown, ChevronUp } from "lucide-react";

export default function AgentTodoPanel({ todos = [], planningComplete, thinkNotes = [] }) {
  const [open, setOpen] = useState(true);
  if (!todos.length && !thinkNotes.length) return null;

  const done = todos.filter((t) => t.status === "done").length;

  return (
    <div
      className="mx-3 mb-1 rounded-lg border text-[11px]"
      style={{ borderColor: "var(--emo-border)", background: "var(--emo-surface)" }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-left"
      >
        <CheckSquare size={12} className="shrink-0 text-[var(--emo-accent)]" />
        <span className="flex-1 font-medium">Plan & todos</span>
        {!planningComplete && (
          <span className="text-[9px] px-1.5 py-0.5 rounded emo-alert-warning shrink-0">plan requis</span>
        )}
        <span className="text-secondary-em shrink-0">{done}/{todos.length}</span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {open && (
        <div className="px-2.5 pb-2 space-y-2 max-h-40 overflow-y-auto">
          {thinkNotes.slice(0, 2).map((n) => (
            <div
              key={n.id || n.ts}
              className="flex gap-1.5 text-[10px] p-1.5 rounded"
              style={{ background: "var(--emo-bg)" }}
            >
              <Brain size={11} className="shrink-0 mt-0.5 opacity-70" />
              <div className="min-w-0">
                <p className="text-secondary-em line-clamp-3">{n.thought}</p>
                {n.next_action && (
                  <p className="text-[var(--emo-accent)] mt-0.5 truncate">→ {n.next_action}</p>
                )}
              </div>
            </div>
          ))}
          <ul className="space-y-0.5">
            {todos.map((t) => (
              <li
                key={t.id}
                className="flex items-start gap-1.5 text-[10px]"
                style={{
                  opacity: t.status === "done" ? 0.5 : 1,
                  color: t.status === "active" ? "var(--emo-accent)" : "var(--emo-text-secondary)",
                }}
              >
                <span className="w-3 shrink-0 text-center">
                  {t.status === "done" ? "✓" : t.status === "active" ? "▸" : "○"}
                </span>
                <span className="truncate">{t.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
