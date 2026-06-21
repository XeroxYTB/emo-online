import React, { useEffect, useState } from "react";
import { AspectRatio } from "./ui/aspect-ratio";
import { Globe, FileText, Image as ImageIcon } from "lucide-react";
import { IFRAME_ALLOW, IFRAME_SANDBOX } from "../lib/iframePreview";

/**
 * Cadre carré réutilisable pour aperçus site / fichier.
 * kind: "iframe" | "image" | "text" | "empty"
 */
function PreviewImage({ src, alt, fallbackSrc, className, style }) {
  const [current, setCurrent] = useState(src);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setCurrent(src);
    setFailed(false);
  }, [src]);

  if (!current || failed) {
    return (
      <div className={`absolute inset-0 flex flex-col items-center justify-center gap-2 text-muted-em p-4 text-center ${className || ""}`}>
        <ImageIcon size={28} className="opacity-40" />
        <span className="text-[11px] opacity-70">{alt || "Aperçu"}</span>
      </div>
    );
  }

  return (
    <img
      src={current}
      alt={alt || "Aperçu"}
      className={className}
      style={style}
      onError={() => {
        if (fallbackSrc && current !== fallbackSrc) {
          setCurrent(fallbackSrc);
          return;
        }
        setFailed(true);
      }}
    />
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
              <PreviewImage
                src={src}
                fallbackSrc={imageFallback}
                alt={title || "Aperçu"}
                className="absolute inset-0 w-full h-full object-contain p-2"
                style={{ background: "var(--emo-preview-bg)" }}
              />
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

export function isImagePath(path = "") {
  const ext = path.split(".").pop()?.toLowerCase() || "";
  return ["png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "ico"].includes(ext);
}

export function previewTextSnippet(content = "", max = 900) {
  const t = (content || "").replace(/\r\n/g, "\n").trim();
  if (!t) return "";
  return t.length > max ? `${t.slice(0, max)}…` : t;
}
