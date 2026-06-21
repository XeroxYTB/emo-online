import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ExternalLink,
  Loader2,
  RefreshCw,
  ArrowDown,
  ArrowUp,
  Keyboard,
  Globe,
  Lock,
} from "lucide-react";
import { toast } from "sonner";
import {
  browserClickAt,
  browserOpen,
  browserScroll,
  browserSnapshot,
  browserKey,
} from "../lib/browserSession";
import { mapImageClickToViewport } from "../lib/browserClickCoords";
import { formatApiError } from "../lib/api";

const SPECIAL_KEYS = new Set([
  "Enter", "Tab", "Escape", "Backspace", "Delete",
  "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
  "Home", "End", "PageUp", "PageDown", "Space",
]);

const SCROLL_THROTTLE_MS = 200;
const SCROLL_SLOW_OVERLAY_MS = 400;

function mapDomKey(e) {
  if (e.ctrlKey || e.metaKey || e.altKey) return null;
  if (e.key === " ") return "Space";
  if (SPECIAL_KEYS.has(e.key)) return e.key;
  if (e.key.length === 1) return { text: e.key };
  return null;
}

function urlLabel(raw) {
  if (!raw) return "";
  try {
    const u = new URL(raw);
    const path = u.pathname === "/" ? "" : u.pathname;
    return `${u.hostname}${path}${u.search}`;
  } catch {
    return raw.replace(/^https?:\/\//, "");
  }
}

function isSecureUrl(raw) {
  try {
    return new URL(raw).protocol === "https:";
  } catch {
    return false;
  }
}

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
  const containerRef = useRef(null);
  const urlInputRef = useRef(null);
  const scrollAccumRef = useRef(0);
  const scrollTimerRef = useRef(null);
  const scrollSlowTimerRef = useRef(null);
  const scrollInFlightRef = useRef(false);
  const [local, setLocal] = useState(frame || null);
  const [loading, setLoading] = useState(false);
  const [scrolling, setScrolling] = useState(false);
  const [scrollSlow, setScrollSlow] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [urlInput, setUrlInput] = useState(frame?.url || "");
  const [clickMark, setClickMark] = useState(null);
  const [keyboardFocused, setKeyboardFocused] = useState(false);
  const autoOpenedRef = useRef(false);

  const pageUrl = local?.url || frame?.url || "";
  const viewportW = local?.viewport_width || frame?.viewport_width || 1280;
  const viewportH = local?.viewport_height || frame?.viewport_height || 900;
  const secure = isSecureUrl(pageUrl);

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

  const runScroll = useCallback(
    async (direction, amount) => {
      if (scrollInFlightRef.current) return;
      scrollInFlightRef.current = true;
      setScrolling(true);
      scrollSlowTimerRef.current = setTimeout(() => setScrollSlow(true), SCROLL_SLOW_OVERLAY_MS);
      try {
        const next = await browserScroll(sessionId, direction, amount);
        if (next) applyFrame(next);
      } catch (e) {
        toast.error(formatApiError(e, "Défilement échoué"));
      } finally {
        clearTimeout(scrollSlowTimerRef.current);
        setScrollSlow(false);
        setScrolling(false);
        scrollInFlightRef.current = false;
      }
    },
    [sessionId, applyFrame],
  );

  const flushScrollAccum = useCallback(() => {
    scrollTimerRef.current = null;
    if (scrollInFlightRef.current) {
      scrollTimerRef.current = setTimeout(flushScrollAccum, SCROLL_THROTTLE_MS);
      return;
    }
    const delta = scrollAccumRef.current;
    scrollAccumRef.current = 0;
    if (Math.abs(delta) < 8) return;
    const direction = delta > 0 ? "down" : "up";
    const amount = Math.round(Math.min(Math.abs(delta) * 1.5, 900));
    runScroll(direction, amount).then(() => {
      if (Math.abs(scrollAccumRef.current) >= 8 && !scrollTimerRef.current) {
        scrollTimerRef.current = setTimeout(flushScrollAccum, SCROLL_THROTTLE_MS);
      }
    });
  }, [runScroll]);

  const handleWheel = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (loading) return;
      scrollAccumRef.current += e.deltaY;
      if (scrollTimerRef.current) return;
      scrollTimerRef.current = setTimeout(flushScrollAccum, SCROLL_THROTTLE_MS);
    },
    [loading, flushScrollAccum],
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el || !hasValidScreenshot(local)) return undefined;
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [handleWheel, local?.screenshot_base64]);

  useEffect(() => {
    return () => {
      if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current);
      if (scrollSlowTimerRef.current) clearTimeout(scrollSlowTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!autoOpen || !pageUrl || hasValidScreenshot(local) || loading || autoOpenedRef.current) return;
    autoOpenedRef.current = true;
    run(() => browserOpen(pageUrl, sessionId));
  }, [autoOpen, pageUrl, local?.screenshot_base64, loading, run, sessionId]);

  const handleKeyDown = useCallback(
    (e) => {
      if (!keyboardFocused || loading) return;
      if (urlInputRef.current && document.activeElement === urlInputRef.current) return;
      const mapped = mapDomKey(e);
      if (!mapped) return;
      e.preventDefault();
      e.stopPropagation();
      if (typeof mapped === "string") {
        run(() => browserKey(sessionId, { key: mapped }));
      } else {
        run(() => browserKey(sessionId, { text: mapped.text }));
      }
    },
    [keyboardFocused, loading, run, sessionId],
  );

  useEffect(() => {
    if (!keyboardFocused) return undefined;
    window.addEventListener("keydown", handleKeyDown, true);
    return () => window.removeEventListener("keydown", handleKeyDown, true);
  }, [keyboardFocused, handleKeyDown]);

  const handleContainerBlur = (e) => {
    requestAnimationFrame(() => {
      const root = containerRef.current;
      if (root && root.contains(document.activeElement)) return;
      setKeyboardFocused(false);
    });
  };

  const screenshotSrc = hasValidScreenshot(local)
    ? `data:image/jpeg;base64,${local.screenshot_base64}`
    : null;

  const handleScreenshotClick = (e) => {
    if (loading || !imgRef.current) return;
    containerRef.current?.focus();
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

  const toolbarBtn =
    "p-1 rounded-md em-hover-subtle flex-shrink-0 disabled:opacity-40 disabled:pointer-events-none transition-opacity";

  if (!pageUrl && !screenshotSrc) return null;

  return (
    <div
      className="rounded-xl overflow-hidden"
      data-testid="interactive-browser"
      style={{
        background: "var(--emo-surface)",
        border: "1px solid var(--emo-border)",
        boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
      }}
    >
      {/* Toolbar */}
      <div
        className="flex items-center gap-1 px-2 py-1.5"
        style={{
          borderBottom: "1px solid var(--emo-border)",
          background: "var(--emo-subtle-bg, var(--emo-surface))",
        }}
      >
        <button
          type="button"
          title="Actualiser"
          disabled={loading}
          onClick={() => run(() => browserSnapshot(sessionId))}
          className={toolbarBtn}
        >
          {loading ? (
            <Loader2 size={13} className="animate-spin" style={{ color: "var(--emo-text-muted)" }} />
          ) : (
            <RefreshCw size={13} style={{ color: "var(--emo-text-muted)" }} />
          )}
        </button>

        <div
          className="flex-1 min-w-0 flex items-center gap-1.5 px-2 py-0.5 rounded-full"
          style={{
            background: "var(--emo-surface)",
            border: "1px solid var(--emo-border)",
          }}
        >
          {secure ? (
            <Lock size={10} className="flex-shrink-0" style={{ color: "var(--emo-text-muted)" }} />
          ) : (
            <Globe size={10} className="flex-shrink-0" style={{ color: "var(--emo-text-muted)" }} />
          )}
          <input
            ref={urlInputRef}
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => {
              e.stopPropagation();
              if (e.key === "Enter" && urlInput.trim()) {
                run(() => browserOpen(urlInput.trim(), sessionId));
              }
            }}
            onFocus={() => setKeyboardFocused(false)}
            placeholder="https://…"
            title={local?.title || pageUrl}
            className="flex-1 min-w-0 bg-transparent border-0 outline-none text-[10px] font-code truncate"
            style={{ color: "var(--emo-text)" }}
            disabled={loading}
          />
        </div>

        {local?.url && (
          <a
            href={local.url}
            target="_blank"
            rel="noopener noreferrer"
            className={toolbarBtn}
            title="Ouvrir dans le navigateur"
          >
            <ExternalLink size={13} style={{ color: "var(--emo-link)" }} />
          </a>
        )}

        <div className="w-px h-4 flex-shrink-0" style={{ background: "var(--emo-border)" }} />

        <button
          type="button"
          title="Défiler vers le haut"
          disabled={loading}
          onClick={() => runScroll("up", 600)}
          className={toolbarBtn}
        >
          <ArrowUp size={13} style={{ color: "var(--emo-text-muted)" }} />
        </button>
        <button
          type="button"
          title="Défiler vers le bas"
          disabled={loading}
          onClick={() => runScroll("down", 600)}
          className={toolbarBtn}
        >
          <ArrowDown size={13} style={{ color: "var(--emo-text-muted)" }} />
        </button>
      </div>

      {/* Viewport */}
      {screenshotSrc ? (
        <div
          ref={containerRef}
          tabIndex={0}
          onFocus={() => setKeyboardFocused(true)}
          onBlur={handleContainerBlur}
          onClick={() => containerRef.current?.focus()}
          className="relative outline-none"
          style={{
            background: "var(--emo-preview-bg)",
            boxShadow: keyboardFocused
              ? "inset 0 0 0 2px var(--mode-color), inset 0 2px 8px rgba(0,0,0,0.12)"
              : "inset 0 2px 8px rgba(0,0,0,0.08)",
          }}
          data-testid="browser-keyboard-capture"
          data-keyboard-focused={keyboardFocused ? "true" : "false"}
        >
          {keyboardFocused && (
            <div
              className="absolute top-2 right-2 z-10 flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-medium pointer-events-none"
              style={{
                background: "rgba(139,92,246,0.88)",
                color: "var(--emo-on-mode)",
              }}
            >
              <Keyboard size={10} />
              Clavier
            </div>
          )}
          <img
            ref={imgRef}
            src={screenshotSrc}
            alt={local?.title || urlLabel(pageUrl) || "Page web"}
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
            <div className="absolute inset-0 flex items-center justify-center bg-black/25 pointer-events-none">
              <Loader2 size={28} className="animate-spin text-white" />
            </div>
          )}
          {scrollSlow && scrolling && !loading && (
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-2 py-1 rounded-full pointer-events-none"
              style={{ background: "rgba(0,0,0,0.55)", color: "#fff" }}
            >
              <Loader2 size={11} className="animate-spin" />
              <span className="text-[9px]">Défilement…</span>
            </div>
          )}
        </div>
      ) : (
        <div
          className="relative flex flex-col items-center justify-center gap-2"
          style={{
            background: "var(--emo-preview-bg)",
            minHeight: compact ? 200 : 320,
            boxShadow: "inset 0 2px 8px rgba(0,0,0,0.08)",
          }}
        >
          {loading ? (
            <>
              <Loader2 size={32} className="animate-spin" style={{ color: "var(--mode-color)" }} />
              <p className="text-xs" style={{ color: "var(--emo-text-muted)" }}>Chargement du navigateur…</p>
            </>
          ) : (
            <>
              <p className="text-xs px-4 text-center" style={{ color: "var(--emo-text-muted)" }}>
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

      {/* Status strip */}
      <div
        className="flex items-center justify-between gap-2 px-2.5 py-1"
        style={{
          borderTop: "1px solid var(--emo-border)",
          color: "var(--emo-text-muted)",
          fontSize: "9px",
        }}
      >
        <span>Clic · Molette · Clavier</span>
        {local?.title && (
          <span className="truncate max-w-[55%] opacity-70" title={local.title}>
            {local.title}
          </span>
        )}
      </div>
    </div>
  );
}
