/** Convertit un clic sur l'image affichée en coordonnées viewport Playwright. */
export function mapImageClickToViewport(img, clientX, clientY, viewportW, viewportH) {
  if (!img || !viewportW || !viewportH) return null;
  const rect = img.getBoundingClientRect();
  const naturalW = img.naturalWidth || viewportW;
  const naturalH = img.naturalHeight || viewportH;
  const scale = Math.min(rect.width / naturalW, rect.height / naturalH);
  const renderedW = naturalW * scale;
  const renderedH = naturalH * scale;
  const offsetX = (rect.width - renderedW) / 2;
  const offsetY = (rect.height - renderedH) / 2;
  const localX = clientX - rect.left - offsetX;
  const localY = clientY - rect.top - offsetY;
  if (localX < 0 || localY < 0 || localX > renderedW || localY > renderedH) return null;
  return {
    x: Math.round((localX / renderedW) * viewportW),
    y: Math.round((localY / renderedH) * viewportH),
  };
}
