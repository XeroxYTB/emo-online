import axios from "axios";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
export { BACKEND_URL };
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";
const SESSION_KEY = "emo_session_token";

export function saveSessionToken(token) {
  if (!token) return;
  try { localStorage.setItem(SESSION_KEY, token); } catch (_) {}
}

export function clearSessionToken() {
  try { localStorage.removeItem(SESSION_KEY); } catch (_) {}
}

export function getSessionToken() {
  try { return localStorage.getItem(SESSION_KEY) || ""; } catch (_) { return ""; }
}

export const http = axios.create({
  baseURL: API,
  withCredentials: true,
});

http.interceptors.request.use((config) => {
  const token = getSessionToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    config.headers["X-Emo-Session"] = token;
  }
  return config;
});

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (!err.response && err.message?.includes("Network Error")) {
      err.message = "Serveur inaccessible. Vérifie ta connexion ou réessaie dans quelques secondes.";
    }
    return Promise.reject(err);
  }
);

export async function streamChat({ conversation_id, content, mode, model_preference, onEvent, signal }) {
  const headers = { "Content-Type": "application/json", Accept: "text/event-stream" };
  const token = getSessionToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    headers["X-Emo-Session"] = token;
  }
  let resp;
  try {
    resp = await fetch(`${API}/chat/stream`, {
      method: "POST",
      credentials: "include",
      headers,
      signal,
      body: JSON.stringify({
        conversation_id,
        content,
        mode,
        model_preference: model_preference || "auto",
      }),
    });
  } catch (e) {
    if (e?.name === "AbortError") {
      onEvent?.({ type: "cancelled" });
      return;
    }
    onEvent?.({
      type: "error",
      content: "Backend inaccessible. Vérifie ta connexion.",
    });
    return;
  }
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      msg = err.detail?.message || err.detail || err.message || msg;
      if (typeof msg === "object") msg = msg.message || JSON.stringify(msg);
    } catch (_) {}
    onEvent?.({ type: "error", content: msg });
    return;
  }
  if (!resp.body) {
    onEvent?.({ type: "error", content: "Reponse vide du serveur" });
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() || "";
      for (const p of parts) {
        const line = p.trim();
        if (!line.startsWith("data:")) continue;
        const json = line.slice(5).trim();
        if (!json) continue;
        try {
          const evt = JSON.parse(json);
          onEvent?.(evt);
        } catch (_) {
          // ignore malformed
        }
      }
    }
  } catch (e) {
    if (e?.name === "AbortError") {
      onEvent?.({ type: "cancelled" });
      return;
    }
    onEvent?.({
      type: "error",
      content: e?.message?.includes("network") || e?.name === "TypeError"
        ? "Connexion perdue pendant la réponse. Réessaie."
        : (e?.message || "Erreur stream"),
    });
  }
}
