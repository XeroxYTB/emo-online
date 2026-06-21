import React, { useState, useEffect, useCallback } from "react";

import { Globe, Search } from "lucide-react";

import SearchResultPreview from "./SearchResultPreview";

import InteractiveBrowser from "./InteractiveBrowser";
import ErrorBoundary from "./ErrorBoundary";

export default function BrowserPanel({ frames = [], reflectNotes = [], onFrameUpdate }) {

  const [activeId, setActiveId] = useState(null);



  useEffect(() => {

    if (frames.length) setActiveId(frames[0].id);

  }, [frames.length, frames[0]?.id]);



  const active = frames.find((f) => f.id === activeId) || frames[0] || null;



  const handleFrameUpdate = useCallback(

    (next) => {

      if (!active?.id) return;

      onFrameUpdate?.(active.id, next);

    },

    [active?.id, onFrameUpdate],

  );



  if (!frames.length && !reflectNotes.length) {

    return (

      <div className="h-full flex flex-col items-center justify-center p-6 text-center" data-testid="browser-panel-empty">

        <Globe size={32} className="text-muted-em opacity-50 mb-3" />

        <p className="text-xs text-muted-em px-4">

          Navigateur interactif — sites ouverts par Émo ou via la barre d&apos;URL.

        </p>

      </div>

    );

  }



  return (

    <div className="h-full flex flex-col" data-testid="browser-panel">

      {reflectNotes.length > 0 && (

        <div className="flex-shrink-0 em-border-b p-2 max-h-28 overflow-y-auto scrollbar-thin space-y-1">

          {reflectNotes.slice(0, 5).map((n) => (

            <div key={n.id} className="text-[10px] rounded-xl px-2.5 py-1.5 emo-btn-soft">

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

              className="w-full text-left px-2.5 py-2 rounded-xl text-[11px] truncate transition"

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

          <PagePreview frame={active} onFrameUpdate={handleFrameUpdate} />

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



function PagePreview({ frame, onFrameUpdate }) {

  return (

    <ErrorBoundary label="Navigateur interactif">

      <InteractiveBrowser

        frame={{

          url: frame.url,

          title: frame.title,

          preview: frame.preview,

          screenshot_base64: frame.screenshot_base64,

          elements: frame.elements,

          session_id: frame.session_id || "default",

          action: frame.action || "control",

        }}

        sessionId={frame.session_id || "default"}

        onFrameUpdate={onFrameUpdate}

      />

    </ErrorBoundary>

  );

}


