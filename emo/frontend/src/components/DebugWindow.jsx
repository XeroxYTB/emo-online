import React, { useEffect, useRef, useState } from "react";
import { http } from "../lib/api";
import { X, Play, Trash2, Bug, Activity, Check, AlertCircle, Loader2, ChevronRight, Filter } from "lucide-react";

const TABS = [
  { id: "events", label: "Events", icon: Activity },
  { id: "selftest", label: "Self-test", icon: Bug },
];

const FILTER_OPTS = [
  { id: "all", label: "Tout" },
  { id: "tool", label: "Tools" },
  { id: "delta", label: "Deltas" },
  { id: "error", label: "Erreurs" },
];

export default function DebugWindow({ events, onClose, onClearEvents }) {
  const [tab, setTab] = useState("events");
  const [filter, setFilter] = useState("all");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [events]);

  const runSelftest = async () => {
    setRunning(true);
    setResults(null);
    try {
      const r = await http.post("/agent/selftest");
      setResults(r.data);
    } catch (e) {
      setResults({ ok: false, error: e?.response?.data?.detail || e.message });
    } finally {
      setRunning(false);
    }
  };

  const filteredEvents = events.filter((e) => {
    if (filter === "all") return true;
    if (filter === "tool") return e.type?.startsWith("tool_");
    if (filter === "delta") return e.type === "delta";
    if (filter === "error") return e.type === "error";
    return true;
  });

  return (
    <div
      data-testid="debug-window"
      className="fixed top-20 right-6 z-50 w-[540px] h-[620px] flex flex-col rounded-2xl overflow-hidden"
      style={{
        background: "rgba(7,4,10,0.95)",
        backdropFilter: "blur(28px)",
        border: "1px solid rgba(6,182,212,0.18)",
        boxShadow: "0 24px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04), 0 0 40px rgba(6,182,212,0.1)",
        animation: "fadeIn 0.2s ease",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: "rgba(6,182,212,0.04)" }}
      >
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Bug size={15} style={{ color: "#06B6D4", filter: "drop-shadow(0 0 6px rgba(6,182,212,0.5))" }} />
            <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          </div>
          <span className="font-heading text-sm font-medium">Debug Console</span>
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted-em">live</span>
        </div>
        <button onClick={onClose} className="p-1.5 rounded hover:bg-white/10 text-muted-em" data-testid="debug-close-btn">
          <X size={14} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-3 pt-2.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = t.id === tab;
          return (
            <button
              key={t.id}
              data-testid={`debug-tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-t-lg text-xs transition relative"
              style={{
                background: active ? "rgba(6,182,212,0.08)" : "transparent",
                color: active ? "#fff" : "var(--emo-text-muted)",
              }}
            >
              <Icon size={12} style={{ color: active ? "#06B6D4" : "currentColor" }} />
              {t.label}
              {active && (
                <span className="absolute bottom-0 left-3 right-3 h-px" style={{ background: "#06B6D4" }} />
              )}
            </button>
          );
        })}
      </div>

      {/* Body */}
      {tab === "events" && (
        <>
          <div className="flex items-center justify-between px-4 py-2 text-[11px]" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
            <div className="flex items-center gap-2">
              <Filter size={11} className="text-muted-em" />
              {FILTER_OPTS.map((f) => (
                <button
                  key={f.id}
                  data-testid={`debug-filter-${f.id}`}
                  onClick={() => setFilter(f.id)}
                  className="px-2 py-0.5 rounded text-[10px] transition"
                  style={{
                    background: filter === f.id ? "rgba(255,255,255,0.06)" : "transparent",
                    color: filter === f.id ? "#fff" : "var(--emo-text-muted)",
                  }}
                >
                  {f.label}
                </button>
              ))}
              <span className="ml-2 text-[10px] text-muted-em">{filteredEvents.length}/{events.length}</span>
            </div>
            <button
              data-testid="debug-clear-events"
              onClick={onClearEvents}
              className="flex items-center gap-1 text-muted-em hover:text-white text-[10px]"
            >
              <Trash2 size={10} /> vider
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin py-1" data-testid="debug-events">
            {filteredEvents.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center px-8">
                <Activity size={28} className="text-muted-em mb-3 opacity-30" />
                <p className="text-xs text-muted-em">En attente d&apos;évènements…</p>
                <p className="text-[10px] text-muted-em mt-1 opacity-70">Lance une conversation pour voir les SSE / tool calls en live.</p>
              </div>
            )}
            {filteredEvents.map((e, i) => (
              <EventLine key={i} evt={e} />
            ))}
          </div>
        </>
      )}

      {tab === "selftest" && (
        <div className="flex-1 overflow-y-auto scrollbar-thin p-5 space-y-4">
          <button
            data-testid="selftest-run-btn"
            onClick={runSelftest}
            disabled={running}
            className="w-full py-3 rounded-2xl text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50 transition-all"
            style={{
              background: "linear-gradient(135deg, #06B6D4 0%, #0891B2 100%)",
              color: "#021824",
              boxShadow: "0 0 24px rgba(6,182,212,0.35), inset 0 1px 0 rgba(255,255,255,0.2)",
            }}
          >
            {running ? <><Loader2 size={14} className="animate-spin" /> En cours…</> : <><Play size={14} /> Diagnostic</>}
          </button>

          {results && (
            <div data-testid="selftest-results" className="space-y-2 mt-1">
              {results.error && (
                <div className="text-xs text-red-300 p-3 rounded-xl flex items-start gap-2" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
                  <AlertCircle size={14} className="mt-0.5 flex-shrink-0" /> {results.error}
                </div>
              )}
              {results.steps?.map((s, i) => (
                <StepCard key={s.step} step={s} index={i + 1} />
              ))}
              {results.steps && (
                <div
                  className="mt-3 p-3 rounded-xl text-xs text-center font-medium"
                  style={{
                    background: results.ok ? "rgba(52,211,153,0.08)" : "rgba(239,68,68,0.08)",
                    border: `1px solid ${results.ok ? "rgba(52,211,153,0.25)" : "rgba(239,68,68,0.25)"}`,
                    color: results.ok ? "#34d399" : "#fca5a5",
                  }}
                >
                  {results.ok
                    ? "✓ Tous les tests passent — agent opérationnel."
                    : "✗ Au moins un test échoue — vérifie l'agent local."}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const StepCard = ({ step, index }) => {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="rounded-xl overflow-hidden transition"
      style={{
        background: step.ok ? "rgba(52,211,153,0.04)" : "rgba(239,68,68,0.04)",
        border: `1px solid ${step.ok ? "rgba(52,211,153,0.18)" : "rgba(239,68,68,0.18)"}`,
      }}
    >
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 px-3 py-2.5 text-left">
        <div className="flex items-center justify-center w-6 h-6 rounded-full text-[10px] font-medium" style={{
          background: step.ok ? "rgba(52,211,153,0.15)" : "rgba(239,68,68,0.15)",
          color: step.ok ? "#34d399" : "#fca5a5",
        }}>
          {step.ok ? <Check size={11} /> : <AlertCircle size={11} />}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[12px] font-medium" style={{ color: step.ok ? "#34d399" : "#fca5a5" }}>
            {index}. {step.label}
          </p>
          <code className="text-[10px] text-muted-em font-code">{step.step}</code>
        </div>
        <ChevronRight size={12} className="opacity-40 transition" style={{ transform: open ? "rotate(90deg)" : "none" }} />
      </button>
      {open && (
        <pre className="px-3 pb-3 font-code text-[10px] overflow-x-auto" style={{ color: "#E9D5FF" }}>
{JSON.stringify(step.result, null, 2)}
        </pre>
      )}
    </div>
  );
};

const EventLine = ({ evt }) => {
  const meta = TYPE_META[evt.type] || { color: "#6D5F82", icon: "·" };
  return (
    <div className="flex items-start gap-2 px-3 py-1 text-[11px] hover:bg-white/[0.02] font-code">
      <span className="text-[9px] text-muted-em w-14 flex-shrink-0 mt-0.5">{evt._t || "--:--:--"}</span>
      <span
        className="w-3 flex-shrink-0 text-center font-bold"
        style={{ color: meta.color }}
      >
        {meta.icon}
      </span>
      <span className="w-20 flex-shrink-0 font-medium" style={{ color: meta.color }}>{evt.type}</span>
      <span className="flex-1 text-secondary-em break-all leading-relaxed">
        {compact(evt)}
      </span>
    </div>
  );
};

const TYPE_META = {
  delta: { color: "#A89BBD", icon: "·" },
  tool_start: { color: "#06B6D4", icon: "▸" },
  tool_executing: { color: "#06B6D4", icon: "▶" },
  tool_result: { color: "#34D399", icon: "✓" },
  done: { color: "#A855F7", icon: "■" },
  error: { color: "#EF4444", icon: "✗" },
};

function compact(evt) {
  const { type, _t, ...rest } = evt;
  if (type === "delta") return `"${(rest.content || "").slice(0, 100)}"`;
  if (type === "tool_start") return `${rest.name} #${rest.id?.slice(-6)}`;
  if (type === "tool_executing") return `${rest.name} ${JSON.stringify(rest.arguments).slice(0, 100)}`;
  if (type === "tool_result") return `${rest.name} → ${rest.result?.ok === false ? "ERR: " + (rest.result?.error || "").slice(0, 60) : "ok"}`;
  if (type === "done") return `mood=${rest.mood} verified=${rest.verified || "-"}`;
  if (type === "error") return rest.content;
  return JSON.stringify(rest).slice(0, 100);
}
