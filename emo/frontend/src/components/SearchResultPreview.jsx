import React from "react";
import { ExternalLink } from "lucide-react";
import SquarePreviewFrame from "./SquarePreviewFrame";
import { domainFromUrl, faviconUrl, resolveSearchResultPreview } from "../lib/sitePreview";

/** Carte résultat de recherche avec miniature / favicon / extrait — pas d'iframe. */
export default function SearchResultPreview({
  url,
  title,
  subtitle,
  snippet,
  className = "",
  testId = "search-result-preview",
  linked = true,
}) {
  if (!url) return null;

  const resolved = resolveSearchResultPreview(url, { snippet });
  const domain = domainFromUrl(url);
  const displayTitle = title || domain || url;
  const displaySubtitle = subtitle || domain || url;
  const imageFallback = faviconUrl(url);

  const frame = (
    <>
      {resolved.kind === "image" && (
        <SquarePreviewFrame
          kind="image"
          src={resolved.src}
          imageFallback={imageFallback}
          title={displayTitle}
          subtitle={displaySubtitle}
          testId={testId}
          className="max-w-none"
        />
      )}
      {resolved.kind === "text" && (
        <SquarePreviewFrame
          kind="text"
          text={resolved.text}
          title={displayTitle}
          subtitle={displaySubtitle}
          testId={testId}
          className="max-w-none"
        />
      )}
      {resolved.kind === "blocked" && (
        imageFallback ? (
          <SquarePreviewFrame
            kind="image"
            src={imageFallback}
            title={displayTitle}
            subtitle={displaySubtitle}
            testId={testId}
            className="max-w-none"
          />
        ) : (
          <SquarePreviewFrame
            kind="empty"
            title={displayTitle}
            subtitle={displaySubtitle}
            emptyLabel={domain || "Site"}
            testId={testId}
            className="max-w-none"
          />
        )
      )}
      {(resolved.blocked || resolved.kind === "blocked") && (
        <span
          className="mt-1.5 text-[10px] flex items-center justify-center gap-1"
          style={{ color: "var(--emo-link)" }}
        >
          Ouvrir
          <ExternalLink size={9} className="flex-shrink-0" />
        </span>
      )}
    </>
  );

  const wrapClass = `block rounded-xl overflow-hidden transition hover:opacity-90 ${className}`;

  if (!linked) {
    return (
      <div className={wrapClass} style={{ border: "1px solid var(--emo-border)" }} data-testid={testId}>
        {frame}
      </div>
    );
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={wrapClass}
      style={{ border: "1px solid var(--emo-border)" }}
      data-testid={testId}
    >
      {frame}
    </a>
  );
}
