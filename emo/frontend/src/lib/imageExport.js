/** Résout une image (data URL ou https) en Blob pour copie / téléchargement. */
export async function fetchImageBlob(src) {
  if (!src) throw new Error("Aucune source image");
  const res = await fetch(src);
  if (!res.ok) throw new Error("Impossible de récupérer l'image");
  return res.blob();
}

export function imageDownloadFilename(blob, prefix = "emo-image") {
  const ext = (blob?.type || "image/png").split("/")[1]?.replace("jpeg", "jpg") || "png";
  return `${prefix}-${Date.now()}.${ext}`;
}

export async function copyImageFromSrc(src) {
  const blob = await fetchImageBlob(src);
  const type = blob.type || "image/png";
  if (!navigator.clipboard?.write || typeof ClipboardItem === "undefined") {
    throw new Error("Presse-papiers indisponible");
  }
  await navigator.clipboard.write([new ClipboardItem({ [type]: blob })]);
}

export function downloadImageBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function downloadImageFromSrc(src, filename) {
  try {
    const blob = await fetchImageBlob(src);
    downloadImageBlob(blob, filename || imageDownloadFilename(blob));
  } catch {
    const a = document.createElement("a");
    a.href = src;
    a.download = filename || `emo-image-${Date.now()}.png`;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
}
