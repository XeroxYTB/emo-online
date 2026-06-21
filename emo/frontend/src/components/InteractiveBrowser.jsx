import React, { useCallback, useEffect, useRef, useState } from "react";
import { ExternalLink, Loader2, RefreshCw, ArrowDown, ArrowUp } from "lucide-react";
import { toast } from "sonner";
import {
  browserClickAt,
  browserOpen,
  browserScroll,
  browserSnapshot,
} from "../lib/browserSession";
import { mapImageClickToViewport } from "../lib/browserClickCoords";
import { formatApiError } from "../lib/api";

/** Navigateur Playwright — clique directement sur la capture d'écran. */
export default function InteractiveBrowser({
  frame,
  sessionId: sessionIdProp,
  onFrameUpdate,
  compact = false,
  autoOpen = true,
}) {
  const sessionId = sessionIdProp || frame?.session_id || "default";
  const imgRef = useRef(null);
  const [local, setLocal] = useState(frame || null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [urlInput, setUrlInput] = useState(frame?.url || "");
  const [clickMark, setClickMark] = useState(null);
  const autoOpenedRef = useRef(false);

  const pageUrl = local?.url || frame?.url || "";
  const viewportW = local?.viewport_width || frame?.viewport_width || 1280;
  const viewportH = local?.viewport_height || frame?.viewport_height || 900;

  useEffect(() => {
    if (frame) {
      setLocal(frame);
      setUrlInput(frame.url || "");
    }
  }, [frame?.url, frame?.screenshot_base64, frame?.elements?.length]);

  const hasValidScreenshot = (data) => {
    const b64 = data?.screenshot_base64;
    if (!b64 || typeof b64 !== "string") return false;
    if (b64.includes("truncated") || b64.includes("[screenshot:")) return false;
    return b64.length > 500;
  };

  const applyFrame = useCallback(
    (next) => {
      if (!next) return;
      setLocal(next);
      setUrlInput(next.url || "");
      setLoadError("");
      onFrameUpdate?.(next);
    },
    [onFrameUpdate],
  );

  const run = useCallback(
    async (fn) => {
      setLoading(true);
      setLoadError("");
      try {
        const next = await fn();
        if (next) applyFrame(next);
        return next;
      } catch (e) {
        const msg = formatApiError(e, "Action navigateur échouée");
        setLoadError(msg);
        toast.error(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [applyFrame],
  );

  useEffect(() => {
    if (!autoOpen || !pageUrl || hasValidScreenshot(local) || loading || autoOpenedRef.current) return;
    autoOpenedRef.current = true;
    run(() => browserOpen(pageUrl, sessionId));
  }, [autoOpen, pageUrl, local?.screenshot_base64, loading, run, sessionId]);

  const screenshotSrc = hasValidScreenshot(local)
    ? `data:image/jpeg;base64,${local.screenshot_base64}`
    : null;

  const handleScreenshotClick = (e) => {
    if (loading || !imgRef.current) return;
    const coords = mapImageClickToViewport(
      imgRef.current,
      e.clientX,
      e.clientY,
      viewportW,
      viewportH,
    );
    if (!coords) return;
    const rect = imgRef.current.getBoundingClientRect();
    setClickMark({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
    setTimeout(() => setClickMark(null), 600);
    run(() => browserClickAt(coords.x, coords.y, sessionId));
  };

  if (!pageUrl && !screenshotSrc) return null;

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

      {screenshotSrc ? (
        <>
          <p className="text-[10px] text-muted-em">Clique directement sur la page</p>
          <div
            className="relative rounded-xl overflow-hidden em-border"
            style={{ background: "var(--emo-preview-bg)" }}
          >
            <img
              ref={imgRef}
              src={screenshotSrc}
              alt={local?.title || "Page web"}
              onClick={handleScreenshotClick}
              className="w-full h-auto block select-none"
              style={{
                maxHeight: compact ? 280 : 520,
                objectFit: "contain",
                objectPosition: "top",
                cursor: loading ? "wait" : "crosshair",
              }}
              draggable={false}
            />
            {clickMark && (
              <span
                className="absolute pointer-events-none rounded-full"
                style={{
                  left: clickMark.x - 8,
                  top: clickMark.y - 8,
                  width: 16,
                  height: 16,
                  border: "2px solid var(--mode-color)",
                  background: "rgba(139,92,246,0.35)",
                }}
              />
            )}
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/20">
                <Loader2 size={28} className="animate-spin text-white" />
              </div>
            )}
          </div>
        </>
      ) : (
        <div
          className="relative rounded-xl overflow-hidden em-border flex flex-col items-center justify-center gap-2"
          style={{
            background: "var(--emo-preview-bg)",
            minHeight: compact ? 200 : 320,
          }}
        >
          {loading ? (
            <>
              <Loader2 size={32} className="animate-spin" style={{ color: "var(--mode-color)" }} />
              <p className="text-xs text-muted-em">Chargement du navigateur…</p>
            </>
          ) : (
            <>
              <p className="text-xs text-muted-em px-4 text-center">
                {loadError || "Appuie sur Entrée dans la barre d'URL pour ouvrir la page."}
              </p>
              {loadError && pageUrl && (
                <button
                  type="button"
                  onClick={() => {
                    autoOpenedRef.current = false;
                    run(() => browserOpen(pageUrl, sessionId));
                  }}
                  className="text-[11px] px-3 py-1.5 rounded-lg font-medium"
                  style={{ background: "var(--mode-color)", color: "var(--emo-on-mode)" }}
                >
                  Réessayer
                </button>
              )}
            </>
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
    </div>
  );
}
