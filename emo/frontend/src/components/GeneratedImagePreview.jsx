import React, { useEffect, useState } from "react";
import { Image as ImageIcon, Copy, Check, Download } from "lucide-react";
import { toast } from "sonner";
import { loadImageDisplaySrc, mergeImageFields } from "../lib/imagePreview";
import { copyImageFromSrc, downloadImageFromSrc } from "../lib/imageExport";

/** Aperçu image générée — chargement robuste (base64 → URL → /b64). */
export default function GeneratedImagePreview({
  sources = [],
  title = "Image générée",
  className = "",
  showActions = true,
  testId = "generated-image-preview",
}) {
  const fields = mergeImageFields(...sources);
  const [src, setSrc] = useState(null);
  const [failed, setFailed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let revokeSrc = null;
    let cancelled = false;
    setSrc(null);
    setFailed(false);

    (async () => {
      const hit = await loadImageDisplaySrc(fields);
      if (cancelled) {
        if (hit?.revoke) URL.revokeObjectURL(hit.src);
        return;
      }
      if (hit?.src) {
        setSrc(hit.src);
        if (hit.revoke) revokeSrc = hit.src;
      } else {
        setFailed(true);
      }
    })();

    return () => {
      cancelled = true;
      if (revokeSrc) URL.revokeObjectURL(revokeSrc);
    };
  }, [fields.image_base64, fields.image_url, fields.mime]);

  const handleCopy = async () => {
    if (!src || busy) return;
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

  const handleSave = async () => {
    if (!src || busy) return;
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
    <div
      className={`w-full max-w-[340px] mx-auto rounded-xl overflow-hidden glass-card ${className}`}
      data-testid={testId}
      style={{ border: "1px solid var(--emo-border)" }}
    >
      <div
        className="relative w-full aspect-square"
        style={{ background: "var(--emo-preview-bg, #111)" }}
      >
        {!src && !failed && (
          <div className="emo-image-gen-placeholder absolute inset-0" aria-hidden />
        )}
        {failed && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-4 text-center">
            <ImageIcon size={28} className="opacity-40" style={{ color: "var(--emo-text-muted)" }} />
            <span className="text-[11px] opacity-70" style={{ color: "var(--emo-text-muted)" }}>
              Image indisponible
            </span>
          </div>
        )}
        {src && (
          <>
            <img
              src={src}
              alt={title || "Image générée"}
              className="absolute inset-0 w-full h-full object-contain p-2 emo-image-reveal"
              decoding="async"
            />
            {showActions && (
              <div className="emo-image-preview-actions absolute bottom-2 right-2 flex gap-1.5 z-10">
                <button
                  type="button"
                  className="emo-icon-btn emo-image-action-btn"
                  title="Copier"
                  disabled={busy}
                  onClick={handleCopy}
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                </button>
                <button
                  type="button"
                  className="emo-icon-btn emo-image-action-btn"
                  title="Enregistrer"
                  disabled={busy}
                  onClick={handleSave}
                >
                  <Download size={14} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
      {title && (
        <p className="mt-2 px-2 pb-2 text-xs font-medium truncate" style={{ color: "var(--emo-text)" }}>
          {title}
        </p>
      )}
    </div>
  );
}
