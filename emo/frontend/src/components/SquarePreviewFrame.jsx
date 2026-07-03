import React, { useEffect, useRef, useState } from "react";
import { AspectRatio } from "./ui/aspect-ratio";
import { Globe, FileText, Image as ImageIcon, Copy, Check, Download } from "lucide-react";
import { toast } from "sonner";
import { IFRAME_ALLOW, IFRAME_SANDBOX } from "../lib/iframePreview";
import { copyImageFromSrc, downloadImageFromSrc } from "../lib/imageExport";
import { isImagePath, previewTextSnippet } from "../lib/previewHelpers";

/** Try JSON base64 fallback when /generated-image URL 404s on HF workers. */
async function fetchGeneratedImageB64(url) {
  if (!url || typeof url !== "string") return null;
  const m = url.match(/\/generated-image\/([^/?]+)(?:\?t=([^&]+))?/);
  if (!m) return null;
  const base = url.split("/generated-image/")[0];
  const token = m[2] || (url.includes("?t=") ? url.split("?t=")[1]?.split("&")[0] : "");
  const b64Url = `${base}/generated-image/${m[1]}/b64${token ? `?t=${token}` : ""}`;
  const resp = await fetch(b64Url, { mode: "cors", credentials: "omit" });
  if (!resp.ok) return null;
  const data = await resp.json();
  const b64 = data?.image_base64;
  if (!b64 || b64.startsWith("[")) return null;
  return `data:${data.mime || "image/png"};base64,${b64}`;
}

async function loadRemoteImageSrc(url) {
  const resp = await fetch(url, { mode: "cors", credentials: "omit" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const blob = await resp.blob();
  if (!blob.type.startsWith("image/") && blob.size < 500) {
    throw new Error("Not an image");
  }
  return URL.createObjectURL(blob);
}

/**
 * Cadre carré réutilisable pour aperçus site / fichier.
 * kind: "iframe" | "image" | "text" | "empty"
 */
function ImagePreviewActions({ src }) {
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleCopy = async (e) => {
    e.stopPropagation();
    if (busy || !src) return;
    setBusy(true);
    try {
      await copyImageFromSrc(src);
      setCopied(true);
      toast.success("Image copiée");
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Copie impossible");
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async (e) => {
    e.stopPropagation();
    if (busy || !src) return;
    setBusy(true);
    try {
      await downloadImageFromSrc(src);
      toast.success("Image enregistrée");
    } catch {
      toast.error("Enregistrement impossible");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="emo-image-preview-actions" data-testid="image-preview-actions">
      <button
        type="button"
        className="emo-icon-btn emo-image-action-btn"
        title="Copier l'image"
        aria-label="Copier"
        disabled={busy}
        data-testid="image-copy-btn"
        onClick={handleCopy}
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>
      <button
        type="button"
        className="emo-icon-btn emo-image-action-btn"
        title="Enregistrer l'image"
        aria-label="Enregistrer"
        disabled={busy}
        data-testid="image-save-btn"
        onClick={handleSave}
      >
        <Download size={14} />
      </button>
    </div>
  );
}

function PreviewImage({ src, alt, fallbackSrc, className, style, showActions = false }) {
  const [current, setCurrent] = useState(null);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const loadedRef = useRef(false);

  useEffect(() => {
    loadedRef.current = loaded;
  }, [loaded]);

  useEffect(() => {
    let objectUrl = null;
    let cancelled = false;

    const applySrc = (next, immediate = false) => {
      if (cancelled || !next) return;
      setCurrent(next);
      setFailed(false);
      const isReady = immediate || next.startsWith("data:") || next.startsWith("blob:");
      setLoaded(isReady);
      loadedRef.current = isReady;
    };

    const fail = () => {
      if (cancelled) return;
      setFailed(true);
      setLoaded(false);
    };

    const tryFallbacks = async (primaryUrl) => {
      if (fallbackSrc && fallbackSrc !== primaryUrl) {
        applySrc(fallbackSrc, fallbackSrc.startsWith("data:"));
        return true;
      }
      if (primaryUrl?.includes("/generated-image/")) {
        try {
          const dataUrl = await fetchGeneratedImageB64(primaryUrl);
          if (dataUrl && !cancelled) {
            applySrc(dataUrl, true);
            return true;
          }
        } catch {
          /* ignore */
        }
      }
      return false;
    };

    if (!src || src.includes("[image:") || src.endsWith("base64,")) {
      fail();
      return () => {};
    }

    if (src.startsWith("data:") || src.startsWith("blob:")) {
      applySrc(src, true);
      return () => {
        cancelled = true;
        if (objectUrl) URL.revokeObjectURL(objectUrl);
      };
    }

    if (src.startsWith("http://") || src.startsWith("https://")) {
      (async () => {
        try {
          objectUrl = await loadRemoteImageSrc(src);
          if (cancelled) return;
          applySrc(objectUrl, true);
        } catch {
          if (cancelled) return;
          const ok = await tryFallbacks(src);
          if (!ok) fail();
        }
      })();
    } else {
      applySrc(src);
    }

    const timer = setTimeout(async () => {
      if (cancelled || loadedRef.current) return;
      const ok = await tryFallbacks(src);
      if (!ok) fail();
    }, 8000);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src, fallbackSrc]);

  if (failed) {
    return (
      <div className={`absolute inset-0 flex flex-col items-center justify-center gap-2 text-muted-em p-4 text-center ${className || ""}`}>
        <ImageIcon size={28} className="opacity-40" />
        <span className="text-[11px] opacity-70">Image indisponible</span>
      </div>
    );
  }

  if (!current) {
    return (
      <div className={`absolute inset-0 ${className || ""}`}>
        <div className="emo-image-gen-placeholder absolute inset-0" aria-hidden />
      </div>
    );
  }

  return (
    <>
      {!loaded && (
        <div className="emo-image-gen-placeholder absolute inset-0" aria-hidden />
      )}
      <img
        src={current}
        alt={alt || "Aperçu"}
        className={`${className || ""} ${loaded ? "emo-image-reveal" : "opacity-0"}`}
        style={style}
        onLoad={() => setLoaded(true)}
        onError={async () => {
          if (fallbackSrc && current !== fallbackSrc) {
            setCurrent(fallbackSrc);
            setLoaded(fallbackSrc.startsWith("data:"));
            return;
          }
          if (current?.includes("/generated-image/")) {
            try {
              const dataUrl = await fetchGeneratedImageB64(current);
              if (dataUrl) {
                setCurrent(dataUrl);
                setLoaded(true);
                return;
              }
            } catch {
              /* ignore */
            }
          }
          setFailed(true);
        }}
      />
      {showActions && loaded && current && (
        <ImagePreviewActions src={current} />
      )}
    </>
  );
}

export default function SquarePreviewFrame({
  kind = "empty",
  url,
  src,
  imageFallback,
  title,
  subtitle,
  text,
  emptyLabel = "Aperçu",
  className = "",
  testId = "square-preview",
  showImageActions = false,
}) {
  return (
    <div className={`w-full max-w-[340px] mx-auto ${className}`} data-testid={testId}>
      <div
        className="rounded-xl overflow-hidden glass-card"
        style={{ border: "1px solid var(--emo-border)" }}
      >
        <AspectRatio ratio={1}>
          <div className="w-full h-full relative" style={{ background: "var(--emo-preview-bg)" }}>
            {kind === "iframe" && url ? (
              <iframe
                title={title || "Aperçu site"}
                src={url}
                className="absolute inset-0 w-full h-full border-0"
                sandbox={IFRAME_SANDBOX}
                allow={IFRAME_ALLOW}
                allowFullScreen
                referrerPolicy="no-referrer-when-downgrade"
              />
            ) : kind === "image" && src ? (
              <div className={`absolute inset-0 ${showImageActions ? "emo-image-preview-wrap" : ""}`}>
                <PreviewImage
                  src={src}
                  fallbackSrc={imageFallback}
                  alt={title || "Aperçu"}
                  className="absolute inset-0 w-full h-full object-contain p-2"
                  style={{ background: "var(--emo-preview-bg)" }}
                  showActions={showImageActions}
                />
              </div>
            ) : kind === "text" && text ? (
              <pre
                className="absolute inset-0 m-0 p-3 text-[10px] leading-relaxed font-code overflow-hidden whitespace-pre-wrap"
                style={{ color: "var(--emo-code-text)" }}
              >
                {text}
              </pre>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-muted-em p-4 text-center">
                {kind === "iframe" ? <Globe size={28} className="opacity-40" /> : null}
                {kind === "text" ? <FileText size={28} className="opacity-40" /> : null}
                {kind === "image" ? <ImageIcon size={28} className="opacity-40" /> : null}
                <span className="text-[11px] opacity-70">{emptyLabel}</span>
              </div>
            )}
          </div>
        </AspectRatio>
      </div>
      {(title || subtitle) && (
        <div className="mt-2 px-1 space-y-0.5">
          {title && <p className="text-xs font-medium truncate">{title}</p>}
          {subtitle && <p className="text-[10px] text-muted-em truncate">{subtitle}</p>}
        </div>
      )}
    </div>
  );
}

export { isImagePath, previewTextSnippet } from "../lib/previewHelpers";
