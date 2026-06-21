const MAX_IMAGES = 4;
const MAX_BYTES = 4 * 1024 * 1024;

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      if (typeof dataUrl !== "string") {
        reject(new Error("Lecture image échouée"));
        return;
      }
      const [header, b64] = dataUrl.split(",");
      resolve({
        preview: dataUrl,
        base64: b64,
        mediaType: header.match(/data:([^;]+)/)?.[1] || "image/jpeg",
        name: file.name,
      });
    };
    reader.onerror = () => reject(reader.error || new Error("Lecture image échouée"));
    reader.readAsDataURL(file);
  });
}

export async function filesToAttachments(files) {
  const list = Array.from(files || []).filter((f) => f.type.startsWith("image/"));
  const out = [];
  for (const file of list) {
    if (file.size > MAX_BYTES) continue;
    try {
      out.push(await readFileAsBase64(file));
    } catch {
      /* skip */
    }
    if (out.length >= MAX_IMAGES) break;
  }
  return out;
}

export function mergeAttachments(existing, incoming, max = MAX_IMAGES) {
  const seen = new Set(existing.map((a) => a.preview));
  const merged = [...existing];
  for (const item of incoming) {
    if (merged.length >= max) break;
    if (seen.has(item.preview)) continue;
    seen.add(item.preview);
    merged.push(item);
  }
  return merged;
}

export { MAX_IMAGES };
