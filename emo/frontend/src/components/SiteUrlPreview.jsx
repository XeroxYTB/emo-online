import React from "react";
import { ExternalLink } from "lucide-react";
import SquarePreviewFrame, { previewTextSnippet } from "./SquarePreviewFrame";
import { resolveSitePreview, faviconUrl } from "../lib/sitePreview";

/** Aperçu URL avec fallback pour sites qui bloquent les iframes (YouTube, etc.). */
export default function SiteUrlPreview({
  url,
  title,
  subtitle,
  previewText,
  screenshotSrc,
  className = "",
  testId = "site-url-preview",
}) {
  if (!url && !screenshotSrc) return null;

  const resolved = resolveSitePreview(url, {
    screenshot: screenshotSrc,
    previewText: previewText ? previewTextSnippet(previewText, 1200) : "",
  });

  return (
    <div className={className} data-testid={testId}>
      {resolved.kind === "iframe" && (
        <SquarePreviewFrame
          kind="iframe"
          url={resolved.url}
          title={title || url}
          subtitle={subtitle || url}
          testId={`${testId}-iframe`}
        />
      )}
      {resolved.kind === "image" && (
        <SquarePreviewFrame
          kind="image"
          src={resolved.src}
          imageFallback={faviconUrl(url)}
          title={title || url}
          subtitle={subtitle || url}
          testId={`${testId}-image`}
        />
      )}
      {resolved.kind === "text" && (
        <SquarePreviewFrame
          kind="text"
          text={resolved.text}
          title={title || url}
          subtitle={subtitle || url}
          testId={`${testId}-text`}
        />
      )}
      {resolved.kind === "blocked" && (
        <SquarePreviewFrame
          kind="image"
          src={faviconUrl(url)}
          title={title || url}
          subtitle={subtitle || url}
          emptyLabel="Aperçu embed indisponible"
          testId={`${testId}-blocked`}
        />
      )}

      {url && (resolved.blocked || resolved.kind === "blocked") && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 text-[11px] flex items-center justify-center gap-1 truncate hover:underline"
          style={{ color: "var(--emo-link)" }}
        >
          Ouvrir dans un nouvel onglet
          <ExternalLink size={10} className="flex-shrink-0" />
        </a>
      )}
    </div>
  );
}
