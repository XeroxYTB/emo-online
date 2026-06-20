import React from "react";
import { Globe, FileText } from "lucide-react";
import { isImagePath, previewTextSnippet } from "./SquarePreviewFrame";
import { htmlPreviewUrl, isHtmlPath } from "../lib/filePreview";

/** Aperçu pleine hauteur pour le panneau Fichiers (HTML rendu, image, texte). */
export default function FilePreviewPane({ path = "", content = "" }) {
  if (!path) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-2 text-muted-em p-6 text-center">
        <FileText size={28} className="opacity-40" />
        <p className="text-xs">Sélectionne un fichier pour l&apos;aperçu</p>
      </div>
    );
  }

  if (isHtmlPath(path) && content) {
    return (
      <div className="flex-1 min-h-0 p-2 flex flex-col" data-testid="file-html-preview">
        <div
          className="flex-1 min-h-[180px] rounded-lg overflow-hidden"
          style={{ border: "1px solid var(--emo-border)", background: "var(--emo-preview-bg)" }}
        >
          <iframe
            title={path}
            src={htmlPreviewUrl(content)}
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin"
          />
        </div>
        <p className="text-[10px] text-muted-em mt-1.5 px-1 flex items-center gap-1">
          <Globe size={10} /> Aperçu HTML rendu
        </p>
      </div>
    );
  }

  if (isImagePath(path) && content.startsWith("data:")) {
    return (
      <div className="flex-1 min-h-0 p-2 flex items-center justify-center" data-testid="file-image-preview">
        <img src={content} alt={path} className="max-w-full max-h-full object-contain rounded-lg" />
      </div>
    );
  }

  if (content) {
    return (
      <div className="flex-1 min-h-0 p-3 overflow-auto scrollbar-thin" data-testid="file-text-preview">
        <pre
          className="text-[11px] leading-relaxed font-code whitespace-pre-wrap m-0"
          style={{ color: "var(--emo-code-text)" }}
        >
          {previewTextSnippet(content, 8000)}
        </pre>
      </div>
    );
  }

  return (
    <div className="flex-1 flex items-center justify-center text-xs text-muted-em">
      Fichier vide
    </div>
  );
}
