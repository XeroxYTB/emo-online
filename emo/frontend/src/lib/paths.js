/** Base path for GitHub Pages (/emo-online) or "" locally */
export const PUBLIC_BASE = (process.env.PUBLIC_URL || "").replace(/\/$/, "");

/** React Router basename */
export const ROUTER_BASENAME = PUBLIC_BASE || undefined;

/** Build an app path with optional GH Pages prefix */
export function appPath(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${PUBLIC_BASE}${p}`;
}

/** Full browser URL for OAuth callbacks etc. */
export function frontendUrl(path = "/") {
  const origin = window.location.origin.replace("localhost", "127.0.0.1");
  return `${origin}${appPath(path)}`;
}
