/** Sites qui refusent l'embed iframe page complète (X-Frame-Options / CSP). */
const IFRAME_BLOCKED =
  /facebook\.com|instagram\.com|twitter\.com|x\.com|tiktok\.com|linkedin\.com|accounts\.google/i;

const YOUTUBE_HOST = /youtube\.com|youtu\.be/i;

export function isIframeBlocked(url = "") {
  try {
    const u = new URL(url);
    return IFRAME_BLOCKED.test(`${u.hostname}${u.pathname}`);
  } catch {
    return false;
  }
}

export function domainFromUrl(url = "") {
  try {
    return new URL(url).hostname.replace(/^www\./i, "");
  } catch {
    return "";
  }
}

export function faviconUrl(url = "", size = 128) {
  const domain = domainFromUrl(url);
  if (!domain) return null;
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=${size}`;
}

export function isYouTubeUrl(url = "") {
  try {
    return YOUTUBE_HOST.test(new URL(url).hostname);
  } catch {
    return false;
  }
}

export function youtubeVideoId(url = "") {
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtu.be")) return u.pathname.slice(1).split("/")[0] || null;
    if (u.hostname.includes("youtube.com")) {
      if (u.pathname === "/watch") return u.searchParams.get("v");
      const m = u.pathname.match(/\/(embed|shorts|v)\/([^/?]+)/);
      return m ? m[2] : null;
    }
  } catch {
    /* ignore */
  }
  return null;
}

/** URL embed YouTube (lecture vidéo dans iframe — youtube.com/watch est bloqué en iframe direct). */
export function youtubeEmbedUrl(url = "") {
  const vid = youtubeVideoId(url);
  if (!vid) return null;
  return `https://www.youtube-nocookie.com/embed/${encodeURIComponent(vid)}?rel=0&modestbranding=1&playsinline=1`;
}

export function siteThumbnail(url = "") {
  const vid = youtubeVideoId(url);
  if (vid) return `https://img.youtube.com/vi/${vid}/hqdefault.jpg`;
  return null;
}

function clipText(text = "", max = 900) {
  const t = String(text || "").replace(/\r\n/g, "\n").trim();
  if (!t) return "";
  return t.length > max ? `${t.slice(0, max)}…` : t;
}

/** Choisit le mode d'aperçu : iframe, image (screenshot/miniature), texte, ou carte bloquée. */
export function resolveSitePreview(url, { screenshot, previewText } = {}) {
  if (screenshot) return { kind: "image", src: screenshot };
  const embed = youtubeEmbedUrl(url);
  if (embed) return { kind: "iframe", url: embed, embed: true };
  const thumb = siteThumbnail(url);
  if (thumb && isYouTubeUrl(url)) {
    return { kind: "image", src: thumb, blocked: true };
  }
  if (isIframeBlocked(url)) {
    if (previewText) return { kind: "text", text: clipText(previewText, 1200), blocked: true };
    const fav = faviconUrl(url);
    if (fav) return { kind: "image", src: fav, blocked: true };
    return { kind: "blocked", url };
  }
  return { kind: "iframe", url };
}

/** Aperçu carte recherche — jamais iframe (trop fragile dans une grille). */
export function resolveSearchResultPreview(url, { snippet } = {}) {
  if (!url) return { kind: "empty" };
  const thumb = siteThumbnail(url);
  if (thumb) return { kind: "image", src: thumb, blocked: true };
  if (snippet && isIframeBlocked(url)) {
    return { kind: "text", text: clipText(snippet, 400), blocked: true };
  }
  const fav = faviconUrl(url);
  if (fav) return { kind: "image", src: fav, blocked: isIframeBlocked(url) };
  if (snippet) return { kind: "text", text: clipText(snippet, 400) };
  return { kind: "blocked", url };
}
