import React, { useState, useEffect } from "react";
import { ExternalLink, Globe, Search, MousePointer2 } from "lucide-react";
import SquarePreviewFrame, { previewTextSnippet } from "./SquarePreviewFrame";

export default function BrowserPanel({ frames = [], reflectNotes = [] }) {
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    if (frames.length) setActiveId(frames[0].id);
  }, [frames.length, frames[0]?.id]);

  const active = frames.find((f) => f.id === activeId) || frames[0] || null;

  if (!frames.length && !reflectNotes.length) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6" data-testid="browser-panel-empty">
        <Globe size={32} className="text-muted-em opacity-50" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" data-testid="browser-panel">
      {reflectNotes.length > 0 && (
        <div className="flex-shrink-0 border-b border-white/5 p-2 max-h-28 overflow-y-auto scrollbar-thin space-y-1">
          {reflectNotes.slice(0, 5).map((n) => (
            <div
              key={n.id}
              className="text-[10px] rounded-lg px-2 py-1.5"
              style={{ background: "rgba(168,85,247,0.12)", border: "1px solid rgba(168,85,247,0.2)" }}
            >
              <span className="text-purple-200 font-medium">💭 </span>
              {n.thought?.slice(0, 180)}
              {n.plan && <span className="block mt-0.5 opacity-70">→ {n.plan.slice(0, 100)}</span>}
            </div>
          ))}
        </div>
      )}

      <div className="flex-shrink-0 max-h-32 overflow-y-auto border-b border-white/5 p-2 space-y-1 scrollbar-thin">
        {frames.map((f) => {
          const isActive = active?.id === f.id;
          const label = f.action === "search"
            ? `🔍 ${f.query || "recherche"}`
            : f.action === "control" || f.screenshot_base64
              ? `🖱 ${f.title || f.url || "Page"}`
              : f.title || f.url || "Page";
          return (
            <button
              key={f.id}
              type="button"
              onClick={() => setActiveId(f.id)}
              className="w-full text-left px-2 py-1.5 rounded-lg text-[11px] truncate transition"
              style={{
                background: isActive ? "rgba(59,130,246,0.15)" : "transparent",
                color: isActive ? "#93c5fd" : "var(--emo-text-secondary)",
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-3">
        {!active ? null : active.action === "search" ? (
          <SearchResults frame={active} />
        ) : (
          <PagePreview frame={active} />
        )}
      </div>
    </div>
  );
}

function SearchResults({ frame }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs text-muted-em">
        <Search size={14} />
        <span>{frame.query}</span>
        <span className="opacity-60">({(frame.results || []).length} résultats)</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {(frame.results || []).slice(0, 8).map((r, i) => (
          <a
            key={r.url || i}
            href={r.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block rounded-xl overflow-hidden transition hover:opacity-90"
            style={{ border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <SquarePreviewFrame
              kind="iframe"
              url={r.url}
              title={r.title || r.url}
              subtitle={r.url}
              testId={`search-preview-${i}`}
              className="max-w-none"
            />
          </a>
        ))}
      </div>
    </div>
  );
}

function PagePreview({ frame }) {
  const url = frame.url || "";
  const screenshotSrc = frame.screenshot_base64
    ? `data:image/jpeg;base64,${frame.screenshot_base64}`
    : null;
  const isControl = Boolean(screenshotSrc || (frame.elements || []).length);

  return (
    <div className="space-y-3">
      <SquarePreviewFrame
        kind={screenshotSrc ? "image" : "iframe"}
        src={screenshotSrc}
        url={!screenshotSrc ? url : undefined}
        title={frame.title || "(sans titre)"}
        subtitle={url}
        testId="visit-square-preview"
      />

      {isControl && (
        <div>
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-em mb-1">
            <MousePointer2 size={11} />
            Éléments cliquables ({(frame.elements || []).length})
          </div>
          <ul className="space-y-1 max-h-36 overflow-y-auto scrollbar-thin">
            {(frame.elements || []).slice(0, 20).map((el) => (
              <li
                key={el.ref}
                className="text-[10px] font-code px-2 py-1 rounded"
                style={{ background: "rgba(255,255,255,0.04)" }}
              >
                <span className="text-[#93c5fd]">[{el.ref}]</span>{" "}
                <span className="opacity-60">{el.tag}</span>{" "}
                {el.text}
              </li>
            ))}
          </ul>
        </div>
      )}

      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] text-[#93c5fd] flex items-center justify-center gap-1 truncate hover:underline"
        >
          Ouvrir dans un nouvel onglet
          <ExternalLink size={10} className="flex-shrink-0" />
        </a>
      )}

      {frame.preview && (
        <div
          className="text-[11px] leading-relaxed whitespace-pre-wrap rounded-xl p-3 max-h-48 overflow-y-auto scrollbar-thin"
          style={{ background: "rgba(0,0,0,0.35)", border: "1px solid rgba(255,255,255,0.06)" }}
        >
          {previewTextSnippet(frame.preview, 1200)}
        </div>
      )}
    </div>
  );
}
