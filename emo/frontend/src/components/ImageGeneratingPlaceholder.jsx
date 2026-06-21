import React from "react";
import { Sparkles } from "lucide-react";
import { AspectRatio } from "./ui/aspect-ratio";

/** Shimmer placeholder while an image is being generated. */
export default function ImageGeneratingPlaceholder({ prompt, className = "" }) {
  return (
    <div
      className={`w-full max-w-[340px] mx-auto ${className}`}
      data-testid="image-gen-placeholder"
    >
      <div
        className="rounded-xl overflow-hidden"
        style={{ border: "1px solid var(--emo-border)" }}
      >
        <AspectRatio ratio={1}>
          <div className="emo-image-gen-placeholder w-full h-full relative flex flex-col items-center justify-center gap-3 p-6">
            <div className="emo-image-gen-sparkles" aria-hidden>
              <Sparkles size={28} style={{ color: "var(--mode-color)" }} />
            </div>
            <p className="text-xs font-medium text-center" style={{ color: "var(--emo-text-secondary)" }}>
              Création de l&apos;image…
            </p>
            {prompt ? (
              <p className="text-[10px] text-center line-clamp-2 max-w-[90%]" style={{ color: "var(--emo-text-muted)" }}>
                {prompt}
              </p>
            ) : null}
          </div>
        </AspectRatio>
      </div>
    </div>
  );
}
