import React, { useEffect, useState } from "react";
import { AspectRatio } from "./ui/aspect-ratio";
import { Globe, FileText, Image as ImageIcon, Copy, Check, Download } from "lucide-react";
import { toast } from "sonner";
import { IFRAME_ALLOW, IFRAME_SANDBOX } from "../lib/iframePreview";
import { copyImageFromSrc, downloadImageFromSrc } from "../lib/imageExport";
import { isImagePath, previewTextSnippet } from "../lib/previewHelpers";

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
  const [current, setCurrent] = useState(src);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!src || src.includes("[image:") || src.endsWith("base64,")) {
      setCurrent(src);
      setFailed(true);
      setLoaded(false);
      return;
    }
    setCurrent(src);
    setFailed(false);
    setLoaded(false);

    const timer = setTimeout(() => {
      setLoaded((wasLoaded) => {
        if (wasLoaded) return true;
        if (fallbackSrc && fallbackSrc !== src) {
          setCurrent(fallbackSrc);
          setFailed(false);
          return false;
        }
        setFailed(true);
        return false;
      });
    }, 25000);

    return () => clearTimeout(timer);
  }, [src, fallbackSrc]);

  if (!current || failed) {
    return (
      <div className={`absolute inset-0 flex flex-col items-center justify-center gap-2 text-muted-em p-4 text-center ${className || ""}`}>
        <ImageIcon size={28} className="opacity-40" />
        <span className="text-[11px] opacity-70">{failed ? "Image indisponible" : (alt || "Aperçu")}</span>
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
        onError={() => {
          if (fallbackSrc && current !== fallbackSrc) {
            setCurrent(fallbackSrc);
            return;
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
