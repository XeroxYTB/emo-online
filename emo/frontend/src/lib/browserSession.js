import { http } from "./api";

function frameFromResult(data) {
  if (!data?.ok) return null;
  return {
    url: data.url,
    title: data.title,
    preview: data.text || data.preview,
    screenshot_base64: data.screenshot_base64,
    elements: data.elements || [],
    session_id: data.session_id || "default",
    action: data.action || "control",
    viewport_width: data.viewport_width || 1280,
    viewport_height: data.viewport_height || 900,
  };
}

export async function browserOpen(url, sessionId = "default") {
  const r = await http.post("/browser/open", { url, session_id: sessionId });
  return frameFromResult(r.data);
}

export async function browserSnapshot(sessionId = "default") {
  const r = await http.post("/browser/snapshot", { session_id: sessionId });
  return frameFromResult(r.data);
}

export async function browserClick(ref, sessionId = "default") {
  const r = await http.post("/browser/click", { ref, session_id: sessionId });
  return frameFromResult(r.data);
}

export async function browserClickAt(x, y, sessionId = "default") {
  const r = await http.post("/browser/click", { x, y, session_id: sessionId });
  return frameFromResult(r.data);
}

export async function browserType(ref, text, sessionId = "default", { clear = false, pressEnter = false } = {}) {
  const r = await http.post("/browser/type", {
    ref,
    text,
    session_id: sessionId,
    clear,
    press_enter: pressEnter,
  });
  return frameFromResult(r.data);
}

export async function browserScroll(sessionId = "default", direction = "down", amount = 600) {
  const r = await http.post("/browser/scroll", { session_id: sessionId, direction, amount });
  return frameFromResult(r.data);
}

export async function browserKey(sessionId = "default", { key, text } = {}) {
  const r = await http.post("/browser/key", { session_id: sessionId, key, text });
  return frameFromResult(r.data);
}
