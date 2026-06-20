import React, { useState, useEffect } from "react";
import { ExternalLink, Globe, Search, MousePointer2 } from "lucide-react";
import SquarePreviewFrame, { previewTextSnippet } from "./SquarePreviewFrame";
import SiteUrlPreview from "./SiteUrlPreview";
import SearchResultPreview from "./SearchResultPreview";

export default function BrowserPanel({ frames = [], reflectNotes = [] }) {
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    if (frames.length) setActiveId(frames[0].id);
  }, [frames.length, frames[0]?.id]);

  const active = frames.find((f) => f.id === activeId) || frames[0] || null;

  if (!frames.length && !reflectNotes.length) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center" data-testid="browser-panel-empty">
        <Globe size={32} className="text-muted-em opacity-50 mb-3" />
        <p className="text-xs text-muted-em px-4">
          Les sites ouverts par Émo s&apos;affichent ici.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" data-testid="browser-panel">
      {reflectNotes.length > 0 && (
        <div className="flex-shrink-0 em-border-b p-2 max-h-28 overflow-y-auto scrollbar-thin space-y-1">
          {reflectNotes.slice(0, 5).map((n) => (
            <div
              key={n.id}
              className="text-[10px] rounded-lg px-2 py-1.5 emo-btn-soft"
            >
              <span className="font-medium" style={{ color: "var(--emo-thought-text)" }}>💭 </span>
              {n.thought?.slice(0, 180)}
              {n.plan && <span className="block mt-0.5 opacity-70">→ {n.plan.slice(0, 100)}</span>}
            </div>
          ))}
        </div>
      )}

      <div className="flex-shrink-0 max-h-32 overflow-y-auto em-border-b p-2 space-y-1 scrollbar-thin">
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
                background: isActive ? "var(--emo-tab-active-bg)" : "transparent",
                color: isActive ? "var(--emo-link)" : "var(--emo-text-secondary)",
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
          <SearchResultPreview
            key={r.url || i}
            url={r.url}
            title={r.title}
            subtitle={r.domain || r.url}
            snippet={r.snippet}
            testId={`search-preview-${i}`}
          />
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
      <SiteUrlPreview
        url={url}
        title={frame.title || "(sans titre)"}
        subtitle={url}
        previewText={frame.preview}
        screenshotSrc={screenshotSrc}
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
                style={{ background: "var(--emo-subtle-bg)" }}
              >
                <span style={{ color: "var(--emo-link)" }}>[{el.ref}]</span>{" "}
                <span className="opacity-60">{el.tag}</span>{" "}
                {el.text}
              </li>
            ))}
          </ul>
        </div>
      )}

      {url && !screenshotSrc && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] flex items-center justify-center gap-1 truncate hover:underline"
          style={{ color: "var(--emo-link)" }}
        >
          Ouvrir dans un nouvel onglet
          <ExternalLink size={10} className="flex-shrink-0" />
        </a>
      )}

      {frame.preview && (
        <div
          className="text-[11px] leading-relaxed whitespace-pre-wrap rounded-xl p-3 max-h-48 overflow-y-auto scrollbar-thin"
          style={{ background: "var(--emo-subtle-bg)", border: "1px solid var(--emo-border)" }}
        >
          {previewTextSnippet(frame.preview, 1200)}
        </div>
      )}
    </div>
  );
}
