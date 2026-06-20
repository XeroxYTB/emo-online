import React, { useCallback, useEffect, useState } from "react";
import { ExternalLink, Loader2, MousePointer2, RefreshCw, ArrowDown, ArrowUp } from "lucide-react";
import { toast } from "sonner";
import {
  browserClick,
  browserOpen,
  browserScroll,
  browserSnapshot,
  browserType,
} from "../lib/browserSession";
import { formatApiError } from "../lib/api";

/** Navigateur Playwright interactif — screenshot + clics sur éléments numérotés. */
export default function InteractiveBrowser({
  frame,
  sessionId: sessionIdProp,
  onFrameUpdate,
  compact = false,
}) {
  const sessionId = sessionIdProp || frame?.session_id || "default";
  const [local, setLocal] = useState(frame || null);
  const [loading, setLoading] = useState(false);
  const [urlInput, setUrlInput] = useState(frame?.url || "");
  const [typeRef, setTypeRef] = useState(null);
  const [typeText, setTypeText] = useState("");

  useEffect(() => {
    if (frame) {
      setLocal(frame);
      setUrlInput(frame.url || "");
    }
  }, [frame?.url, frame?.screenshot_base64, frame?.elements?.length]);

  const applyFrame = useCallback(
    (next) => {
      if (!next) return;
      setLocal(next);
      setUrlInput(next.url || "");
      onFrameUpdate?.(next);
    },
    [onFrameUpdate],
  );

  const run = useCallback(
    async (fn) => {
      setLoading(true);
      try {
        const next = await fn();
        if (next) applyFrame(next);
        return next;
      } catch (e) {
        toast.error(formatApiError(e, "Action navigateur échouée"));
        return null;
      } finally {
        setLoading(false);
      }
    },
    [applyFrame],
  );

  const screenshotSrc =
    local?.screenshot_base64 &&
    !String(local.screenshot_base64).includes("truncated")
      ? `data:image/jpeg;base64,${local.screenshot_base64}`
      : null;

  const elements = local?.elements || [];

  if (!local && !screenshotSrc) return null;

  return (
    <div className="space-y-2" data-testid="interactive-browser">
      <div className="flex gap-1.5 items-center">
        <input
          type="url"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && urlInput.trim()) {
              run(() => browserOpen(urlInput.trim(), sessionId));
            }
          }}
          placeholder="https://…"
          className="flex-1 min-w-0 px-2 py-1 rounded-lg text-[11px] font-code em-input"
          disabled={loading}
        />
        <button
          type="button"
          title="Actualiser"
          disabled={loading}
          onClick={() => run(() => browserSnapshot(sessionId))}
          className="p-1.5 rounded-lg em-hover-subtle flex-shrink-0"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
        </button>
        {local?.url && (
          <a
            href={local.url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg em-hover-subtle flex-shrink-0"
            title="Ouvrir dans le navigateur"
          >
            <ExternalLink size={14} style={{ color: "var(--emo-link)" }} />
          </a>
        )}
      </div>

      {local?.title && (
        <p className="text-[11px] font-medium truncate" style={{ color: "var(--emo-text)" }}>
          {local.title}
        </p>
      )}

      {screenshotSrc && (
        <div
          className="relative rounded-xl overflow-hidden em-border"
          style={{ background: "var(--emo-preview-bg)" }}
        >
          <img
            src={screenshotSrc}
            alt={local?.title || "Page web"}
            className="w-full h-auto block"
            style={{ maxHeight: compact ? 220 : 420, objectFit: "contain", objectPosition: "top" }}
          />
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/30">
              <Loader2 size={28} className="animate-spin text-white" />
            </div>
          )}
        </div>
      )}

      <div className="flex gap-1">
        <button
          type="button"
          disabled={loading}
          onClick={() => run(() => browserScroll(sessionId, "up"))}
          className="flex items-center gap-1 px-2 py-1 rounded text-[10px] em-hover-subtle"
        >
          <ArrowUp size={10} /> Haut
        </button>
        <button
          type="button"
          disabled={loading}
          onClick={() => run(() => browserScroll(sessionId, "down"))}
          className="flex items-center gap-1 px-2 py-1 rounded text-[10px] em-hover-subtle"
        >
          <ArrowDown size={10} /> Bas
        </button>
      </div>

      {elements.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-em mb-1.5">
            <MousePointer2 size={11} />
            Clique pour interagir ({elements.length})
          </div>
          <div
            className={`grid gap-1 max-h-${compact ? "28" : "40"} overflow-y-auto scrollbar-thin`}
            style={{ maxHeight: compact ? 112 : 160 }}
          >
            {elements.slice(0, compact ? 12 : 24).map((el) => (
              <button
                key={el.ref}
                type="button"
                disabled={loading}
                onClick={() => {
                  if (el.tag === "input" || el.tag === "textarea") {
                    setTypeRef(el.ref);
                    setTypeText(el.text?.startsWith("[") ? "" : el.text || "");
                  } else {
                    run(() => browserClick(el.ref, sessionId));
                  }
                }}
                className="text-left text-[10px] px-2 py-1.5 rounded-lg transition em-hover-subtle truncate"
                style={{
                  background: typeRef === el.ref ? "var(--emo-tab-active-bg)" : "var(--emo-subtle-bg)",
                  border: "1px solid var(--emo-border)",
                }}
              >
                <span style={{ color: "var(--emo-link)" }}>[{el.ref}]</span>{" "}
                <span className="opacity-50">{el.tag}</span> {el.text}
              </button>
            ))}
          </div>
        </div>
      )}

      {typeRef != null && (
        <div className="flex gap-1.5">
          <input
            value={typeText}
            onChange={(e) => setTypeText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && typeText.trim()) {
                run(() =>
                  browserType(typeRef, typeText, sessionId, { clear: true, pressEnter: false }),
                ).then(() => setTypeRef(null));
              }
            }}
            placeholder={`Texte pour [${typeRef}]…`}
            className="flex-1 px-2 py-1 rounded-lg text-[11px] em-input"
            disabled={loading}
          />
          <button
            type="button"
            disabled={loading || !typeText.trim()}
            onClick={() =>
              run(() =>
                browserType(typeRef, typeText, sessionId, { clear: true, pressEnter: true }),
              ).then(() => setTypeRef(null))
            }
            className="px-2 py-1 rounded-lg text-[10px] font-medium flex-shrink-0"
            style={{ background: "var(--mode-color)", color: "var(--emo-on-mode)" }}
          >
            Envoyer
          </button>
        </div>
      )}
    </div>
  );
}
