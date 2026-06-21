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
  browserKeyFire,
} from "../lib/browserSession";
import { mapImageClickToViewport } from "../lib/browserClickCoords";
import { formatApiError } from "../lib/api";

const SPECIAL_KEYS = new Set([
  "Enter", "Tab", "Escape", "Backspace", "Delete",
  "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
  "Home", "End", "PageUp", "PageDown", "Space",
]);

const SCROLL_THROTTLE_MS = 16;
const KEY_SNAPSHOT_MS = 80;

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
  embedded = false,
}) {
  const sessionId = sessionIdProp || frame?.session_id || "default";
  const imgRef = useRef(null);
  const containerRef = useRef(null);
  const urlInputRef = useRef(null);
  const scrollAccumRef = useRef(0);
  const scrollTimerRef = useRef(null);
  const scrollPendingRef = useRef(false);
  const keySnapshotTimerRef = useRef(null);
  const flushScrollAccumRef = useRef(() => {});
  const actionGenRef = useRef(0);
  const [local, setLocal] = useState(frame || null);
  const [navigating, setNavigating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
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

  const runNavigate = useCallback(
    async (fn) => {
      setNavigating(true);
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
        setNavigating(false);
      }
    },
    [applyFrame],
  );

  const runRefresh = useCallback(
    async (fn) => {
      const gen = ++actionGenRef.current;
      setRefreshing(true);
      try {
        const next = await fn();
        if (next && gen === actionGenRef.current) applyFrame(next);
        return next;
      } catch (e) {
        toast.error(formatApiError(e, "Action navigateur échouée"));
        return null;
      } finally {
        if (gen === actionGenRef.current) setRefreshing(false);
      }
    },
    [applyFrame],
  );

  const scheduleKeySnapshot = useCallback(() => {
    if (keySnapshotTimerRef.current) clearTimeout(keySnapshotTimerRef.current);
    keySnapshotTimerRef.current = setTimeout(() => {
      keySnapshotTimerRef.current = null;
      runRefresh(() => browserSnapshot(sessionId));
    }, KEY_SNAPSHOT_MS);
  }, [runRefresh, sessionId]);

  const runScroll = useCallback(
    async (direction, amount) => {
      if (scrollPendingRef.current) return;
      scrollPendingRef.current = true;
      try {
        await runRefresh(() => browserScroll(sessionId, direction, amount));
      } finally {
        scrollPendingRef.current = false;
        if (Math.abs(scrollAccumRef.current) >= 8 && !scrollTimerRef.current) {
          scrollTimerRef.current = setTimeout(
            () => flushScrollAccumRef.current(),
            SCROLL_THROTTLE_MS,
          );
        }
      }
    },
    [sessionId, runRefresh],
  );

  const flushScrollAccum = useCallback(() => {
    scrollTimerRef.current = null;
    const delta = scrollAccumRef.current;
    scrollAccumRef.current = 0;
    if (Math.abs(delta) < 8) return;
    const direction = delta > 0 ? "down" : "up";
    const amount = Math.round(Math.min(Math.abs(delta) * 1.2, 720));
    runScroll(direction, amount);
  }, [runScroll]);

  flushScrollAccumRef.current = flushScrollAccum;

  const handleWheel = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (navigating) return;
      scrollAccumRef.current += e.deltaY;
      if (scrollTimerRef.current) return;
      scrollTimerRef.current = setTimeout(
        () => flushScrollAccumRef.current(),
        SCROLL_THROTTLE_MS,
      );
    },
    [navigating],
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
      if (keySnapshotTimerRef.current) clearTimeout(keySnapshotTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!autoOpen || !pageUrl || hasValidScreenshot(local) || navigating || autoOpenedRef.current) return;
    autoOpenedRef.current = true;
    runNavigate(() => browserOpen(pageUrl, sessionId));
  }, [autoOpen, pageUrl, local?.screenshot_base64, navigating, runNavigate, sessionId]);

  const handleKeyDown = useCallback(
    (e) => {
      if (!keyboardFocused || navigating) return;
      if (urlInputRef.current && document.activeElement === urlInputRef.current) return;
      const mapped = mapDomKey(e);
      if (!mapped) return;
      e.preventDefault();
      e.stopPropagation();
      const payload = typeof mapped === "string" ? { key: mapped } : { text: mapped.text };
      browserKeyFire(sessionId, payload).catch(() => {});
      scheduleKeySnapshot();
    },
    [keyboardFocused, navigating, sessionId, scheduleKeySnapshot],
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
    if (navigating || !imgRef.current) return;
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
    runRefresh(() => browserClickAt(coords.x, coords.y, sessionId));
  };

  const busy = navigating;

  const toolbarBtn =
    "p-1.5 rounded-xl em-hover-subtle flex-shrink-0 disabled:opacity-40 disabled:pointer-events-none transition-all";

  if (!pageUrl && !screenshotSrc) return null;

  const outerRadius = embedded ? "var(--emo-radius-lg)" : "var(--emo-radius-xl)";

  return (
    <div
      className="overflow-hidden"
      data-testid="interactive-browser"
      style={{
        background: "var(--emo-surface)",
        border: embedded ? "none" : "1px solid var(--emo-border)",
        borderRadius: outerRadius,
        boxShadow: embedded ? "none" : "0 4px 24px rgba(0,0,0,0.06)",
      }}
    >
      {/* Chrome toolbar */}
      <div
        className="flex items-center gap-1.5 px-2.5 py-2"
        style={{
          borderBottom: "1px solid var(--emo-border)",
          background: "var(--emo-subtle-bg, var(--emo-surface))",
        }}
      >
        <div className="hidden sm:flex items-center gap-1 flex-shrink-0 px-0.5" aria-hidden>
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#f87171" }} />
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#fbbf24" }} />
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#34d399" }} />
        </div>

        <button
          type="button"
          title="Actualiser"
          disabled={busy}
          onClick={() => runRefresh(() => browserSnapshot(sessionId))}
          className={toolbarBtn}
        >
          {refreshing ? (
            <Loader2 size={14} className="animate-spin" style={{ color: "var(--emo-accent)" }} />
          ) : (
            <RefreshCw size={14} style={{ color: "var(--emo-text-muted)" }} />
          )}
        </button>

        <div
          className="flex-1 min-w-0 flex items-center gap-2 px-3 py-1.5"
          style={{
            background: "var(--emo-input-bg)",
            border: "1px solid var(--emo-border)",
            borderRadius: "var(--emo-radius-xl)",
          }}
        >
          {secure ? (
            <Lock size={11} className="flex-shrink-0" style={{ color: "var(--emo-success-text)" }} />
          ) : (
            <Globe size={11} className="flex-shrink-0" style={{ color: "var(--emo-text-muted)" }} />
          )}
          <input
            ref={urlInputRef}
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => {
              e.stopPropagation();
              if (e.key === "Enter" && urlInput.trim()) {
                runNavigate(() => browserOpen(urlInput.trim(), sessionId));
              }
            }}
            onFocus={() => setKeyboardFocused(false)}
            placeholder="https://…"
            title={local?.title || pageUrl}
            className="flex-1 min-w-0 bg-transparent border-0 outline-none text-[11px] font-code truncate"
            style={{ color: "var(--emo-text)" }}
            disabled={busy}
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
            <ExternalLink size={14} style={{ color: "var(--emo-link)" }} />
          </a>
        )}

        <div className="w-px h-5 flex-shrink-0 mx-0.5" style={{ background: "var(--emo-border)" }} />

        <button
          type="button"
          title="Défiler vers le haut"
          disabled={busy}
          onClick={() => runScroll("up", 480)}
          className={toolbarBtn}
        >
          <ArrowUp size={14} style={{ color: "var(--emo-text-muted)" }} />
        </button>
        <button
          type="button"
          title="Défiler vers le bas"
          disabled={busy}
          onClick={() => runScroll("down", 480)}
          className={toolbarBtn}
        >
          <ArrowDown size={14} style={{ color: "var(--emo-text-muted)" }} />
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
              ? "inset 0 0 0 2px var(--emo-accent), inset 0 2px 12px rgba(0,0,0,0.08)"
              : "inset 0 2px 12px rgba(0,0,0,0.06)",
          }}
          data-testid="browser-keyboard-capture"
          data-keyboard-focused={keyboardFocused ? "true" : "false"}
        >
          {keyboardFocused && (
            <div
              className="absolute top-3 right-3 z-10 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium pointer-events-none"
              style={{
                background: "var(--emo-accent)",
                color: "var(--emo-on-accent)",
                boxShadow: "0 4px 12px var(--emo-glow)",
              }}
            >
              <Keyboard size={11} />
              Clavier actif
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
              cursor: busy ? "wait" : "crosshair",
            }}
            draggable={false}
          />
          {clickMark && (
            <span
              className="absolute pointer-events-none rounded-full"
              style={{
                left: clickMark.x - 9,
                top: clickMark.y - 9,
                width: 18,
                height: 18,
                border: "2px solid var(--emo-accent)",
                background: "var(--emo-accent-soft)",
              }}
            />
          )}
          {refreshing && (
            <div
              className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-0.5 rounded-full pointer-events-none text-[9px]"
              style={{ background: "var(--emo-surface)", border: "1px solid var(--emo-border)", color: "var(--emo-text-muted)" }}
              aria-hidden
            >
              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "var(--emo-accent)" }} />
              MàJ
            </div>
          )}
        </div>
      ) : (
        <div
          className="relative flex flex-col items-center justify-center gap-3 px-4"
          style={{
            background: "var(--emo-preview-bg)",
            minHeight: compact ? 200 : 320,
            boxShadow: "inset 0 2px 12px rgba(0,0,0,0.06)",
          }}
        >
          {navigating ? (
            <>
              <Loader2 size={36} className="animate-spin" style={{ color: "var(--emo-accent)" }} />
              <p className="text-xs text-center" style={{ color: "var(--emo-text-muted)" }}>Chargement du navigateur…</p>
            </>
          ) : (
            <>
              <Globe size={28} style={{ color: "var(--emo-text-muted)", opacity: 0.5 }} />
              <p className="text-xs px-4 text-center" style={{ color: "var(--emo-text-muted)" }}>
                {loadError || "Appuie sur Entrée dans la barre d'URL pour ouvrir la page."}
              </p>
              {loadError && pageUrl && (
                <button
                  type="button"
                  onClick={() => {
                    autoOpenedRef.current = false;
                    runNavigate(() => browserOpen(pageUrl, sessionId));
                  }}
                  className="text-[11px] px-4 py-2 rounded-xl font-medium transition-opacity hover:opacity-90"
                  style={{ background: "var(--emo-accent)", color: "var(--emo-on-accent)" }}
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
        className="flex items-center justify-between gap-2 px-3 py-1.5"
        style={{
          borderTop: "1px solid var(--emo-border)",
          background: "var(--emo-subtle-bg, var(--emo-surface))",
          color: "var(--emo-text-muted)",
          fontSize: "10px",
        }}
      >
        <span className="flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full" style={{ background: busy ? "#fbbf24" : "var(--emo-status-online)" }} />
          Clic · Molette · Clavier
        </span>
        {local?.title && (
          <span className="truncate max-w-[55%] opacity-80 font-medium" title={local.title}>
            {local.title}
          </span>
        )}
      </div>
    </div>
  );
}
