import { getApiBase } from "./api";

/** Displayable base64 (not a UI placeholder). */
export function isUsableImageBase64(b64) {
  return b64 && typeof b64 === "string" && !b64.startsWith("[") && b64.length > 100;
}

/** Resolve relative API paths to absolute URLs. */
export function resolveImageUrl(url) {
  if (!url || typeof url !== "string") return null;
  if (url.startsWith("data:")) {
    if (url.includes("[image:") || url.endsWith("base64,") || url.length < 120) return null;
    return url;
  }
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  const apiBase = getApiBase().replace(/\/$/, "");
  const path = url.startsWith("/") ? url : `/${url}`;
  if (path.startsWith("/generated-image/")) {
    return `${apiBase}${path}`;
  }
  if (path.startsWith("/api/")) {
    return `${apiBase.replace(/\/api$/, "")}${path}`;
  }
  return `${apiBase}${path}`;
}

/** Build data URL from raw base64 + mime. */
export function base64ToDataUrl(b64, mime = "image/png") {
  if (!isUsableImageBase64(b64)) return null;
  return `data:${mime || "image/png"};base64,${b64}`;
}

/** `/generated-image/{id}?t=…` → `/generated-image/{id}/b64?t=…` */
export function generatedImageB64Endpoint(imageUrl) {
  const resolved = resolveImageUrl(imageUrl);
  if (!resolved?.includes("/generated-image/")) return null;
  return resolved.replace(/\/generated-image\/([^/?]+)/, "/generated-image/$1/b64");
}

export function collectImageFields(input) {
  if (!input || typeof input !== "object") {
    return { image_base64: null, image_url: null, mime: "image/png", title: null, has_image: false };
  }
  return {
    image_base64: input.image_base64 || null,
    image_url: input.image_url || null,
    mime: input.mime || "image/png",
    title: input.title || input.prompt || input.subject || null,
    has_image: Boolean(input.has_image),
  };
}

export function mergeImageFields(...sources) {
  const out = { image_base64: null, image_url: null, mime: "image/png", title: null, has_image: false };
  for (const src of sources) {
    const f = collectImageFields(src);
    if (isUsableImageBase64(f.image_base64)) out.image_base64 = f.image_base64;
    if (f.image_url) out.image_url = f.image_url;
    if (f.mime && f.mime !== "image/png") out.mime = f.mime;
    if (f.title) out.title = f.title;
    if (f.has_image) out.has_image = true;
  }
  return out;
}

/** Best display src without network — data URL or resolved http(s) URL for <img src>. */
export function resolveImageDisplaySrc({ image_base64, image_url, mime = "image/png" }) {
  const dataUrl = base64ToDataUrl(image_base64, mime);
  if (dataUrl) return dataUrl;
  return resolveImageUrl(image_url);
}

/** Fetch JSON base64 fallback when direct URL fails. */
export async function fetchImageB64DataUrl(imageUrl, mime = "image/png") {
  const endpoint = generatedImageB64Endpoint(imageUrl);
  if (!endpoint) return null;
  try {
    const resp = await fetch(endpoint, { mode: "cors", credentials: "omit" });
    if (!resp.ok) return null;
    const data = await resp.json();
    return base64ToDataUrl(data?.image_base64, data?.mime || mime);
  } catch {
    return null;
  }
}

async function blobSrcFromDataUrl(dataUrl) {
  const resp = await fetch(dataUrl);
  if (!resp.ok) return null;
  const blob = await resp.blob();
  if (!blob || blob.size < 500) return null;
  return URL.createObjectURL(blob);
}

/** Load a displayable src for <img> — blob URL preferred over huge data: URLs. */
export async function loadRenderableImageSrc(fields) {
  const mime = fields?.mime || "image/png";
  const dataUrl = base64ToDataUrl(fields?.image_base64, mime);
  if (dataUrl) {
    try {
      const blobSrc = await blobSrcFromDataUrl(dataUrl);
      if (blobSrc) return { src: blobSrc, revoke: true };
    } catch {
      /* try URL fallbacks */
    }
  }

  const url = resolveImageUrl(fields?.image_url);
  if (url) {
    try {
      const resp = await fetch(url, { mode: "cors", credentials: "omit" });
      if (resp.ok) {
        const blob = await resp.blob();
        if (blob.size > 500 && (blob.type.startsWith("image/") || blob.size > 2000)) {
          return { src: URL.createObjectURL(blob), revoke: true };
        }
      }
    } catch {
      /* try /b64 */
    }
    const fromJson = await fetchImageB64DataUrl(url, mime);
    if (fromJson) {
      try {
        const blobSrc = await blobSrcFromDataUrl(fromJson);
        if (blobSrc) return { src: blobSrc, revoke: true };
      } catch {
        return { src: fromJson, revoke: false };
      }
    }
  }

  if (dataUrl) return { src: dataUrl, revoke: false };
  return null;
}
