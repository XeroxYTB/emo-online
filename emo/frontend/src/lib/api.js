import axios from "axios";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
const BACKEND_FALLBACK = (process.env.REACT_APP_BACKEND_FALLBACK_URL || "").replace(/\/$/, "");
export { BACKEND_URL, BACKEND_FALLBACK };
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

async function _fetchWithFallback(path, options = {}) {
  const bases = [BACKEND_URL, BACKEND_FALLBACK].filter(Boolean);
  if (!bases.length) bases.push("");
  let lastErr;
  for (const base of bases) {
    const url = base ? `${base}/api${path}` : `/api${path}`;
    try {
      const r = await fetch(url, options);
      if (r.status === 429 || r.status === 503) {
        await new Promise((res) => setTimeout(res, 2000));
        continue;
      }
      return r;
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("Backend inaccessible");
}
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
    if (err.response?.status === 429) {
      err.message = "API surchargée (429). Attends 30 secondes et réessaie.";
    } else if (!err.response && err.message?.includes("Network Error")) {
      err.message = "Serveur inaccessible. Vérifie ta connexion ou réessaie dans quelques secondes.";
    }
    return Promise.reject(err);
  }
);

export async function streamChat({ conversation_id, content, mode, model_preference, use_agent_tools, onEvent, signal }) {
  const headers = { "Content-Type": "application/json", Accept: "text/event-stream" };
  const token = getSessionToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    headers["X-Emo-Session"] = token;
  }
  let terminal = false;
  const finish = (evt) => {
    if (evt?.type === "done" || evt?.type === "error" || evt?.type === "cancelled") terminal = true;
    onEvent?.(evt);
  };
  let resp;
  try {
    resp = await _fetchWithFallback("/chat/stream", {
      method: "POST",
      credentials: "include",
      headers,
      signal,
      body: JSON.stringify({
        conversation_id,
        content,
        mode,
        model_preference: model_preference || "auto",
        use_agent_tools: use_agent_tools !== false,
      }),
    });
  } catch (e) {
    if (e?.name === "AbortError") {
      finish({ type: "cancelled" });
      return;
    }
    finish({
      type: "error",
      content: "Backend inaccessible. Vérifie ta connexion.",
    });
    return;
  }
  if (resp.status === 429) {
    finish({
      type: "error",
      content: "API surchargée (429). Attends 30 secondes et réessaie.",
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
    finish({ type: "error", content: msg });
    return;
  }
  if (!resp.body) {
    finish({ type: "error", content: "Reponse vide du serveur" });
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
          finish(JSON.parse(json));
        } catch (_) {
          // ignore malformed
        }
      }
    }
    if (!terminal) {
      finish({
        type: "error",
        content: "Réponse incomplète — la connexion s'est coupée. Réessaie.",
      });
    }
  } catch (e) {
    if (e?.name === "AbortError") {
      finish({ type: "cancelled" });
      return;
    }
    finish({
      type: "error",
      content: e?.message?.includes("network") || e?.name === "TypeError"
        ? "Connexion perdue pendant la réponse. Réessaie."
        : (e?.message || "Erreur stream"),
    });
  }
}

export async function wakeBackend(maxAttempts = 4) {
  const bases = [BACKEND_URL, BACKEND_FALLBACK].filter(Boolean);
  if (!bases.length) bases.push("");
  for (let i = 0; i < maxAttempts; i++) {
    for (const base of bases) {
      try {
        const url = base ? `${base}/api/ping` : "/api/ping";
        const r = await fetch(url, { credentials: "include", cache: "no-store" });
        if (r.ok) return { ok: true, base: base || "same-origin" };
        if (r.status === 429) {
          await new Promise((res) => setTimeout(res, 2500 * (i + 1)));
        }
      } catch (_) {
        await new Promise((res) => setTimeout(res, 1500));
      }
    }
  }
  return { ok: false };
}
