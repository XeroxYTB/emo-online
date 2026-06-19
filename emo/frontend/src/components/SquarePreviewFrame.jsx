import React from "react";
import { AspectRatio } from "./ui/aspect-ratio";
import { Globe, FileText, Image as ImageIcon } from "lucide-react";

/**
 * Cadre carré réutilisable pour aperçus site / fichier.
 * kind: "iframe" | "image" | "text" | "empty"
 */
export default function SquarePreviewFrame({
  kind = "empty",
  url,
  src,
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
        style={{ border: "1px solid rgba(255,255,255,0.08)" }}
      >
        <AspectRatio ratio={1}>
          <div className="w-full h-full bg-[#07040a] relative">
            {kind === "iframe" && url ? (
              <iframe
                title={title || "Aperçu site"}
                src={url}
                className="absolute inset-0 w-full h-full border-0"
                sandbox="allow-scripts allow-same-origin allow-forms"
                referrerPolicy="no-referrer"
              />
            ) : kind === "image" && src ? (
              <img
                src={src}
                alt={title || "Aperçu"}
                className="absolute inset-0 w-full h-full object-contain bg-black/60 p-2"
              />
            ) : kind === "text" && text ? (
              <pre
                className="absolute inset-0 m-0 p-3 text-[10px] leading-relaxed font-code overflow-hidden whitespace-pre-wrap"
                style={{ color: "#E9D5FF" }}
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
