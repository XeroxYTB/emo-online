import React, { useState } from "react";
import { ChevronDown, ChevronUp, Layers } from "lucide-react";

export default function ProjectPlanStrip({ plan }) {
  const [open, setOpen] = useState(false);
  if (!plan?.phases?.length) return null;

  const phases = plan.phases;
  const idx = plan.current_phase_index ?? 0;
  const active = phases[idx];
  const done = phases.filter((p) => p.status === "done").length;

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
        <Layers size={12} className="shrink-0 text-[var(--emo-accent)]" />
        <span className="flex-1 truncate font-medium">
          {plan.title?.slice(0, 60) || "Méga-projet"}
        </span>
        <span className="text-secondary-em shrink-0">
          {idx + 1}/{phases.length} · {done} ✓
        </span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {active && (
        <p className="px-2.5 pb-1 text-[10px] text-[var(--emo-accent)] truncate">
          En cours : {active.name}
        </p>
      )}
      {open && (
        <ul className="px-2.5 pb-2 space-y-0.5 max-h-32 overflow-y-auto">
          {phases.map((p, i) => (
            <li
              key={p.id ?? i}
              className="flex items-center gap-1.5 text-[10px]"
              style={{
                opacity: p.status === "done" ? 0.55 : 1,
                color: i === idx ? "var(--emo-accent)" : "var(--emo-text-secondary)",
              }}
            >
              <span className="w-3 text-center">{p.status === "done" ? "✓" : i === idx ? "▸" : "○"}</span>
              <span className="truncate">{p.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
