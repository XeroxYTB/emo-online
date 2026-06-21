import React, { useEffect, useRef, useState, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { http, streamChat, clearSessionToken, wakeBackend } from "../lib/api";
import { toast } from "sonner";
import { PanelRightOpen, PanelRightClose, Clock, User as UserIcon, Menu, ArrowDown } from "lucide-react";
import Sidebar from "../components/Sidebar";
import ChatComposer from "../components/ChatComposer";
import ChatMessage from "../components/ChatMessage";
import EmoEyes from "../components/EmoEyes";
import { AppTopBar } from "../components/EmoLogo";
import RightPanel from "../components/RightPanel";
import Paywall from "../components/SubscriptionPlans";
import ProfileDrawer from "../components/ProfileDrawer";
import { cleanDisplayText } from "../lib/messageClean";
import { isHtmlPath, normalizeFilePath } from "../lib/filePreview";

const MODE_LABELS = { tech: "Tech", creatif: "Créatif", brutal: "Brutal" };

function cleanStreamText(text) {
  return cleanDisplayText(text);
}

export default function Chat() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(location.state?.user || null);
  const [authState, setAuthState] = useState(location.state?.user ? "ok" : "checking");

  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [mode, setMode] = useState("tech");
  const [streaming, setStreaming] = useState(false);
  const [streamingMsg, setStreamingMsg] = useState(null);
  const [streamingTools, setStreamingTools] = useState([]); // tools in current streaming turn
  const [agentOnline, setAgentOnline] = useState(false);
  const [allTools, setAllTools] = useState([]);
  const [filePreview, setFilePreview] = useState(null);
  const [liveHtmlByPath, setLiveHtmlByPath] = useState({});
  const [browserFrames, setBrowserFrames] = useState([]);
  const handleBrowserFrameUpdate = useCallback((frameId, next) => {
    setBrowserFrames((prev) =>
      prev.map((f) =>
        f.id === frameId
          ? {
              ...f,
              url: next.url,
              title: next.title,
              preview: next.preview,
              screenshot_base64: next.screenshot_base64,
              elements: next.elements,
              session_id: next.session_id,
              action: next.action || "control",
            }
          : f,
      ),
    );
  }, []);
  const [reflectNotes, setReflectNotes] = useState([]);
  const [rightPanelTab, setRightPanelTab] = useState("activity");
  const [rightOpen, setRightOpen] = useState(true);
  const [debugEvents, setDebugEvents] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    typeof window !== "undefined" && localStorage.getItem("emo_sidebar_collapsed") === "1"
  );
  const [sidebarOpenMobile, setSidebarOpenMobile] = useState(false);
  const [license, setLicense] = useState(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [themeMode, setThemeMode] = useState(
    typeof window !== "undefined" ? (localStorage.getItem("emo_theme_mode") || "dark") : "dark"
  );
  const [modelPreference, setModelPreference] = useState(
    typeof window !== "undefined" ? (localStorage.getItem("emo_model_preference") || "auto") : "auto"
  );
  const [useAgentTools, setUseAgentTools] = useState(
    typeof window !== "undefined" ? localStorage.getItem("emo_use_agent_tools") !== "0" : true
  );
  const [availableModels, setAvailableModels] = useState([{ id: "auto", label: "Auto" }]);
  const chatAreaRef = useRef(null);
  const stickyBottomRef = useRef(true);
  const streamAbortRef = useRef(null);
  const themeSyncedRef = useRef(false);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const isNearBottom = useCallback((el, threshold = 140) => {
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  }, []);

  const scrollToBottom = useCallback((behavior = "smooth") => {
    const el = chatAreaRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
    stickyBottomRef.current = true;
    setShowScrollBtn(false);
  }, []);

  useEffect(() => {
    const el = chatAreaRef.current;
    if (!el) return;
    const onScroll = () => {
      const near = isNearBottom(el);
      stickyBottomRef.current = near;
      setShowScrollBtn(!near && (messages.length > 0 || streaming));
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [isNearBottom, messages.length, streaming]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("emo_sidebar_collapsed", sidebarCollapsed ? "1" : "0");
    }
  }, [sidebarCollapsed]);

  // Load preferences
  useEffect(() => {
    if (authState !== "ok") return;
    wakeBackend({ maxWaitMs: 8000 }).catch(() => {});
  }, [authState]);

  useEffect(() => {
    if (authState !== "ok" || themeSyncedRef.current) return;
    http.get("/profile").then((r) => {
      const p = r.data.preferences || {};
      const localTheme = localStorage.getItem("emo_theme_mode");
      if (p.theme_mode && !localTheme) setThemeMode(p.theme_mode);
      themeSyncedRef.current = true;
    }).catch(() => {
      themeSyncedRef.current = true;
    });
  }, [authState]);

  useEffect(() => {
    if (authState !== "ok") return;
    http.get("/llm/models").then((r) => {
      if (r.data?.models?.length) setAvailableModels(r.data.models);
    }).catch(() => {});
  }, [authState]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("emo_model_preference", modelPreference || "auto");
    }
  }, [modelPreference]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("emo_use_agent_tools", useAgentTools ? "1" : "0");
    }
  }, [useAgentTools]);

  // Apply theme (dark/light/system) to <html>
  useEffect(() => {
    const html = document.documentElement;
    const apply = (mode) => {
      let resolved = mode;
      if (mode === "system") {
        resolved = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
      }
      html.classList.remove("theme-dark", "theme-light");
      html.classList.add(`theme-${resolved}`);
      html.style.colorScheme = resolved;
    };
    apply(themeMode);
    localStorage.setItem("emo_theme_mode", themeMode);
    if (themeMode === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: light)");
      const handler = () => apply("system");
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, [themeMode]);

  const pushDebug = useCallback((evt) => {
    const now = new Date();
    const t = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
    setDebugEvents((prev) => [...prev, { ...evt, _t: t }].slice(-500));
  }, []);

  // License polling
  useEffect(() => {
    if (authState !== "ok") return;
    const tick = async () => {
      try {
        const r = await http.get("/license/status");
        setLicense(r.data);
      } catch { /* ignore */ }
    };
    tick();
    // Check for stripe return
    const params = new URLSearchParams(window.location.search);
    const sid = params.get("stripe_session_id");
    if (sid) {
      pollPayment(sid);
      window.history.replaceState({}, document.title, "/chat");
    }
  }, [authState]);

  const pollPayment = async (sessionId, attempt = 0) => {
    if (attempt > 10) {
      toast.error("Timeout vérification paiement");
      return;
    }
    try {
      const r = await http.get(`/license/checkout/status/${sessionId}`);
      if (r.data.payment_status === "paid") {
        toast.success("Paiement confirmé.");
        const lr = await http.get("/license/status");
        setLicense(lr.data);
        return;
      }
      setTimeout(() => pollPayment(sessionId, attempt + 1), 2000);
    } catch (e) {
      setTimeout(() => pollPayment(sessionId, attempt + 1), 2000);
    }
  };

  // Auth check
  useEffect(() => {
    if (user) {
      setAuthState("ok");
      return undefined;
    }
    let cancelled = false;
    const timeoutId = setTimeout(() => {
      if (!cancelled) setAuthState("timeout");
    }, 15000);
    http.get("/auth/me", { timeout: 12000 })
      .then((res) => {
        if (cancelled) return;
        setUser(res.data);
        setAgentOnline(!!res.data.agent_online);
        setAuthState("ok");
      })
      .catch(() => {
        if (!cancelled) setAuthState("no");
        navigate("/login", { replace: true });
      })
      .finally(() => clearTimeout(timeoutId));
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [user, navigate]);

  // Poll agent status every 4s
  useEffect(() => {
    if (authState !== "ok") return;
    const tick = async () => {
      try {
        const r = await http.get("/agent/status");
        setAgentOnline(r.data.online);
      } catch { /* ignore */ }
    };
    tick();
    const id = setInterval(tick, 4000);
    return () => clearInterval(id);
  }, [authState]);

  const refreshAgentStatus = useCallback(async () => {
    const r = await http.get("/agent/status");
    setAgentOnline(r.data.online);
  }, []);

  // Load conversations
  useEffect(() => {
    if (authState !== "ok") return;
    http.get("/conversations").then((r) => {
      setConversations(r.data);
      if (r.data.length > 0 && !activeId) setActiveId(r.data[0].conversation_id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authState]);

  // Load messages for active conv
  useEffect(() => {
    if (!activeId) { setMessages([]); return; }
    http.get(`/conversations/${activeId}/messages`).then((r) => setMessages(r.data));
    const c = conversations.find((cv) => cv.conversation_id === activeId);
    if (c?.mode) setMode(c.mode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  // Auto-scroll uniquement si l'utilisateur est déjà en bas (ne bloque pas la lecture)
  useEffect(() => {
    if (!stickyBottomRef.current) return;
    const el = chatAreaRef.current;
    if (!el) return;
    const behavior = streaming ? "auto" : "smooth";
    requestAnimationFrame(() => {
      el.scrollTo({ top: el.scrollHeight, behavior });
    });
  }, [messages, streamingMsg, streamingTools, streaming]);

  const handleNew = async () => {
    const r = await http.post("/conversations", { title: "Nouvelle conversation", mode });
    setConversations((cs) => [r.data, ...cs]);
    setActiveId(r.data.conversation_id);
    setMessages([]);
  };

  const handleRename = async (id, title) => {
    await http.patch(`/conversations/${id}`, { title });
    setConversations((cs) => cs.map((c) => c.conversation_id === id ? { ...c, title } : c));
  };

  const handleDelete = async (id) => {
    await http.delete(`/conversations/${id}`);
    setConversations((cs) => cs.filter((c) => c.conversation_id !== id));
    if (id === activeId) { setActiveId(null); setMessages([]); }
  };

  const handleLogout = async () => {
    await http.post("/auth/logout");
    clearSessionToken();
    navigate("/login", { replace: true });
  };

  const handleCancel = useCallback(() => {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    setStreaming(false);
    setStreamingMsg(null);
    setStreamingTools([]);
  }, []);

  useEffect(() => {
    if (!streaming) return;
    const onKey = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        handleCancel();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [streaming, handleCancel]);

  const attachInlinePreview = (turnTools, preview) => {
    if (!turnTools.length) return turnTools;
    const updated = [...turnTools];
    let idx = updated.length - 1;
    if (preview.type === "file") {
      const previewPath = preview.path ? normalizeFilePath(preview.path) : "";
      let matched = false;
      for (let i = updated.length - 1; i >= 0; i -= 1) {
        const tool = updated[i].tool;
        if (!["write_file", "read_file", "edit_file"].includes(tool)) continue;
        const toolPath = updated[i].args?.path || updated[i].result?.path || "";
        if (previewPath && toolPath && normalizeFilePath(toolPath) === previewPath) {
          idx = i;
          matched = true;
          break;
        }
      }
      if (!matched) {
        for (let i = updated.length - 1; i >= 0; i -= 1) {
          if (["write_file", "read_file", "edit_file"].includes(updated[i].tool)) {
            idx = i;
            break;
          }
        }
      }
    } else if (preview.type === "browser") {
      for (let i = updated.length - 1; i >= 0; i -= 1) {
        if ([
          "browser_visit", "browser_open", "web_fetch", "web_search",
          "browser_click", "browser_snapshot", "browser_scroll", "browser_press", "browser_type",
        ].includes(updated[i].tool)) {
          idx = i;
          break;
        }
      }
    }
    updated[idx] = { ...updated[idx], inlinePreview: preview };
    return updated;
  };

  const buildFilePreview = (path, content) => {
    if (!path || content == null) return null;
    const ext = (path.split(".").pop() || "").toLowerCase();
    return {
      type: "file",
      path,
      preview: String(content).slice(0, 50000),
      is_image: ["png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "ico"].includes(ext),
      language: ext,
    };
  };

  const syncLiveHtml = (path, content) => {
    if (!path || content == null || !isHtmlPath(path)) return;
    const preview = String(content).slice(0, 50000);
    const key = normalizeFilePath(path);
    setLiveHtmlByPath((prev) => ({ ...prev, [key]: preview, [path]: preview }));
  };

  const buildBrowserPreview = (tool, args, result) => {
    const url = args.url || result?.url;
    if (!url && !result?.screenshot_base64) return null;
    return {
      type: "browser",
      action: tool === "browser_open" ? "control" : "control",
      url: url || result?.url || "",
      title: result?.title,
      preview: result?.preview || result?.text,
      screenshot_base64: result?.screenshot_base64,
      elements: result?.elements || [],
      session_id: result?.session_id || args.session_id || "default",
    };
  };

  const BROWSER_PREVIEW_TOOLS = [
    "browser_visit", "browser_open", "web_fetch",
    "browser_click", "browser_snapshot", "browser_scroll", "browser_press", "browser_type",
  ];

  const handleSend = async (text, images = [], imageMediaTypes = []) => {
    if (streaming) return;
    if (!text.trim() && !images.length) return;
    let convId = activeId;
    if (!convId) {
      const r = await http.post("/conversations", { title: "Nouvelle conversation", mode });
      convId = r.data.conversation_id;
      setConversations((cs) => [r.data, ...cs]);
      setActiveId(convId);
    }
    const optimistic = {
      message_id: `tmp_${Date.now()}`, role: "user", content: text, mode,
      images: images.length ? images : undefined,
    };
    setMessages((m) => [...m, optimistic]);
    stickyBottomRef.current = true;
    scrollToBottom("auto");
    setStreaming(true);
    setStreamingMsg({ content: "" });
    setStreamingTools([]);

    let buffer = "";
    const turnTools = []; // local accumulator
    const abortController = new AbortController();
    streamAbortRef.current = abortController;
    const streamTimeout = setTimeout(() => {
      abortController.abort();
      toast.error("Délai dépassé.");
    }, 180000);

    try {
      await streamChat({
        conversation_id: convId, content: text, images,
        image_media_types: imageMediaTypes.length ? imageMediaTypes : undefined,
        mode,
        model_preference: modelPreference || "auto",
        use_agent_tools: useAgentTools,
        signal: abortController.signal,
        onEvent: (evt) => {
          pushDebug(evt);
          if (evt.type === "delta") {
            buffer += evt.content;
            const display = cleanStreamText(buffer);
            setStreamingMsg({ content: display });
          } else if (evt.type === "tool_start") {
            turnTools.push({ id: evt.id, tool: evt.name, args: {}, state: "executing", result: null });
            setStreamingTools([...turnTools]);
            setAllTools((prev) => [...turnTools, ...prev.filter((t) => !turnTools.find((tt) => tt.id === t.id))].slice(0, 50));
          } else if (evt.type === "tool_executing") {
            const i = turnTools.findIndex((t) => t.id === evt.id);
            if (i >= 0) turnTools[i].args = evt.arguments || {};
            setStreamingTools([...turnTools]);
          } else if (evt.type === "tool_result") {
            const i = turnTools.findIndex((t) => t.id === evt.id);
            if (i >= 0) {
              turnTools[i].result = evt.result;
              turnTools[i].state = evt.result?.ok === false ? "error" : "done";
              const tool = turnTools[i].tool;
              const args = turnTools[i].args || {};
              if (evt.result?.ok !== false) {
                if (tool === "write_file") {
                  const filePath = args.path || evt.result?.path;
                  const fileContent = args.content || evt.result?.content;
                  const fp = buildFilePreview(filePath, fileContent);
                  if (fp) turnTools[i].inlinePreview = fp;
                  syncLiveHtml(filePath, fileContent);
                } else if (tool === "edit_file") {
                  const filePath = args.path || evt.result?.path;
                  const fileContent = evt.result?.content || evt.result?.preview;
                  const fp = buildFilePreview(filePath, fileContent);
                  if (fp) turnTools[i].inlinePreview = fp;
                  syncLiveHtml(filePath, fileContent);
                } else if (tool === "read_file" && evt.result?.content) {
                  const filePath = args.path || evt.result?.path;
                  const fp = buildFilePreview(filePath, evt.result.content);
                  if (fp) turnTools[i].inlinePreview = fp;
                  syncLiveHtml(filePath, evt.result.content);
                } else if (tool === "web_search" && evt.result?.results?.length) {
                  turnTools[i].inlinePreview = {
                    type: "browser",
                    action: "search",
                    query: evt.result.query || args.query || "",
                    results: (evt.result.results || []).slice(0, 8),
                  };
                } else if (BROWSER_PREVIEW_TOOLS.includes(tool)) {
                  const bp = buildBrowserPreview(tool, args, evt.result);
                  if (bp) turnTools[i].inlinePreview = bp;
                }
              }
            }
            setStreamingTools([...turnTools]);
            setAllTools((prev) => {
              const updated = [...prev];
              const idx = updated.findIndex((t) => t.id === evt.id);
              if (idx >= 0) updated[idx] = turnTools[i];
              return updated;
            });
          } else if (evt.type === "browser") {
            const preview = { type: "browser", ...evt };
            const frameId = `bf_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
            setBrowserFrames((prev) => [{ id: frameId, ...evt }, ...prev].slice(0, 24));
            if (turnTools.length) {
              const updated = attachInlinePreview(turnTools, preview);
              turnTools.splice(0, turnTools.length, ...updated);
              setStreamingTools([...turnTools]);
            } else {
              turnTools.push({
                id: frameId,
                tool: "browser_visit",
                state: "done",
                args: { url: evt.url || "" },
                result: { ok: true, url: evt.url, title: evt.title, preview: evt.preview },
                inlinePreview: preview,
              });
              setStreamingTools([...turnTools]);
            }
          } else if (evt.type === "reflect") {
            const note = { id: `rn_${Date.now()}`, ...evt };
            setReflectNotes((prev) => [note, ...prev].slice(0, 12));
          } else if (evt.type === "image") {
            turnTools.push({
              id: evt.id || `img_${Date.now()}`,
              tool: "image_output",
              state: "done",
              args: {},
              result: { ok: true },
              inlinePreview: {
                type: "file",
                path: evt.title || "image",
                preview: evt.src,
                is_image: true,
              },
            });
            setStreamingTools([...turnTools]);
          } else if (evt.type === "file_preview") {
            const preview = { type: "file", ...evt };
            if (turnTools.length) {
              const updated = attachInlinePreview(turnTools, preview);
              turnTools.splice(0, turnTools.length, ...updated);
            } else {
              turnTools.push({
                id: `fp_${Date.now()}`,
                tool: "write_file",
                state: "done",
                args: { path: evt.path },
                result: { ok: true, path: evt.path },
                inlinePreview: preview,
              });
            }
            setStreamingTools([...turnTools]);
            syncLiveHtml(evt.path, evt.preview);
            if (useAgentTools) {
              setFilePreview({
                path: evt.path,
                preview: evt.preview,
                is_image: evt.is_image,
                language: evt.language,
              });
              setRightPanelTab("files");
            }
          } else if (evt.type === "done") {
            const finalContent = cleanStreamText(buffer).trim();
            setMessages((m) => [
              ...m,
              {
                message_id: evt.message_id, role: "emo",
                content: finalContent, mood: evt.mood, verified: evt.verified, mode,
                tool_calls_live: turnTools,
              },
            ]);
            setStreamingMsg(null);
            setStreamingTools([]);
            if (evt.title) {
              setConversations((cs) =>
                cs.map((c) => c.conversation_id === convId ? { ...c, title: evt.title, updated_at: new Date().toISOString() } : c)
              );
            } else {
              setConversations((cs) =>
                cs.map((c) => c.conversation_id === convId ? { ...c, updated_at: new Date().toISOString() } : c)
              );
            }
          } else if (evt.type === "ping") {
            // keepalive SSE — connexion toujours active
          } else if (evt.type === "error") {
            toast.error(evt.content || "Erreur.");
            setStreamingMsg(null);
            setStreamingTools([]);
          } else if (evt.type === "cancelled") {
            setStreamingMsg(null);
            setStreamingTools([]);
          }
        },
      });
    } catch (e) {
      if (e?.name !== "AbortError") {
        toast.error(e?.message || "Connexion interrompue.");
      }
      setStreamingMsg(null);
      setStreamingTools([]);
    } finally {
      clearTimeout(streamTimeout);
      if (streamAbortRef.current === abortController) {
        streamAbortRef.current = null;
      }
      setStreaming(false);
    }
  };

  if (authState === "checking") {
    return (
      <div className="login-page h-screen w-full flex flex-col">
        <AppTopBar />
        <div className="flex-1 flex flex-col items-center justify-center gap-3">
          <p className="text-sm text-secondary-em">Chargement…</p>
          <div className="dot-loading"><span /><span /><span /></div>
        </div>
      </div>
    );
  }

  if (authState === "timeout") {
    return (
      <div className="login-page h-screen w-full flex flex-col">
        <AppTopBar />
        <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6 text-center">
          <p className="text-sm text-secondary-em">Connexion lente — le serveur HF démarre peut‑être.</p>
          <button
            type="button"
            onClick={async () => {
              setAuthState("checking");
              try {
                await wakeBackend({ maxWaitMs: 30000 });
                const res = await http.get("/auth/me", { timeout: 15000 });
                setUser(res.data);
                setAgentOnline(!!res.data.agent_online);
                setAuthState("ok");
              } catch {
                navigate("/login", { replace: true });
              }
            }}
            className="px-4 py-2 rounded-xl text-sm font-medium"
            style={{ background: "var(--emo-accent)", color: "var(--emo-on-accent)" }}
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  const hasMessages = messages.length > 0 || streamingMsg;

  return (
    <div
      className={`mode-${mode} h-screen w-full flex overflow-hidden`}
    >
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNew}
        onRename={handleRename}
        onDelete={handleDelete}
        user={user}
        onLogout={handleLogout}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed(!sidebarCollapsed)}
        onOpenProfile={() => setProfileOpen(true)}
      />

      <main className="flex-1 flex flex-col h-full min-h-0 min-w-0 overflow-hidden relative">
        {/* Header */}
        <header
          data-testid="chat-header"
          className="flex-shrink-0 px-3 md:px-5 h-14 flex items-center justify-between gap-2 border-b emo-panel-flat"
          style={{ borderColor: "var(--emo-border)", background: "var(--emo-surface)" }}
        >
          <div className="flex items-center gap-2 md:gap-3 min-w-0">
            <button
              data-testid="mobile-menu-btn"
              onClick={() => setSidebarOpenMobile(true)}
              className="md:hidden p-2 rounded-xl em-hover-subtle text-muted-em"
              aria-label="Ouvrir le menu"
            >
              <Menu size={18} />
            </button>
            <div className="min-w-0">
              <p className="font-heading text-sm font-medium leading-none">{MODE_LABELS[mode] || "Chat"}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 md:gap-2 flex-shrink-0">
            {license && license.active && license.tier === "free" && !license.is_admin && (
              <span
                data-testid="trial-pill"
                className="hidden md:inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] px-2.5 py-1 rounded-full"
                style={{ background: "rgba(168,85,247,0.1)", color: "var(--mode-color)" }}
              >
                <Clock size={10} /> {license.messages_left_today}/{license.messages_per_day}
              </span>
            )}
            <button
              data-testid="header-profile-btn"
              onClick={() => setProfileOpen(true)}
              className="p-2 rounded-xl em-hover text-muted-em transition"
              title="Paramètres"
            >
              <UserIcon size={15} />
            </button>
            <button
              data-testid="toggle-right-panel"
              onClick={() => setRightOpen(!rightOpen)}
              className="hidden md:inline-flex p-2 rounded-xl em-hover text-muted-em"
              title="Panneau latéral"
            >
              {rightOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
            </button>
          </div>
        </header>

        {/* Zone messages — flex au lieu de position absolute pour un scroll fiable */}
        <div className="flex-1 min-h-0 relative flex flex-col">
          <div
            ref={chatAreaRef}
            data-testid="chat-area"
            className="flex-1 min-h-0 overflow-y-auto overscroll-contain scrollbar-thin chat-scroll-area"
            style={{ background: "var(--emo-bg)" }}
          >
            {!hasMessages && (
              <div className="h-full min-h-[280px] flex flex-col items-center justify-center px-6">
                <EmoEyes mode={mode} mood={null} size={130} />
              </div>
            )}

            <div className="max-w-4xl mx-auto px-4 md:px-8 pt-6 pb-6 space-y-7">
              {messages.map((m) => (
                <ChatMessage
                  key={m.message_id}
                  message={m}
                  liveHtmlByPath={liveHtmlByPath}
                  showCopyCode={!useAgentTools}
                />
              ))}
              {(streamingMsg || streamingTools.length > 0) && (
                <ChatMessage
                  key="streaming"
                  message={{
                    role: "emo",
                    content: streamingMsg?.content || "",
                    mood: null, mode,
                    tool_calls_live: streamingTools,
                  }}
                  isStreaming
                  liveHtmlByPath={liveHtmlByPath}
                  showCopyCode={!useAgentTools}
                />
              )}
            </div>
          </div>

          {showScrollBtn && (
            <button
              type="button"
              onClick={() => scrollToBottom("smooth")}
              className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium shadow-lg transition hover:scale-105"
              style={{
                background: "var(--emo-surface)",
                border: "1px solid var(--emo-border)",
                color: "var(--emo-text-secondary)",
                boxShadow: "var(--emo-drawer-shadow)",
              }}
              aria-label="Revenir en bas"
            >
              <ArrowDown size={14} />
              {streaming ? "En cours" : "Bas"}
            </button>
          )}
        </div>

        {/* Composer — dans le flux flex, plus en absolute */}
        <div
          className="flex-shrink-0 z-10 px-3 md:px-4 pb-4 md:pb-5 pt-3"
          style={{
            borderTop: "1px solid var(--emo-border)",
            background: "linear-gradient(to top, var(--emo-bg) 80%, transparent)",
          }}
        >
          <div className="max-w-4xl mx-auto">
            <ChatComposer
              mode={mode}
              onChangeMode={setMode}
              modelPreference={modelPreference}
              onChangeModelPreference={setModelPreference}
              availableModels={availableModels}
              useAgentTools={useAgentTools}
              onChangeUseAgentTools={setUseAgentTools}
              onSend={handleSend}
              onCancel={handleCancel}
              disabled={false}
              streaming={streaming}
            />
          </div>
        </div>
      </main>

      {/* Right panel: hidden on small screens (kept for desktop only) */}
      {rightOpen && (
        <div className="hidden md:block">
          <RightPanel
            tools={allTools}
            agentOnline={agentOnline}
            onRefreshStatus={refreshAgentStatus}
            filePreview={filePreview}
            activeTab={rightPanelTab}
            onTabChange={setRightPanelTab}
            browserFrames={browserFrames}
            reflectNotes={reflectNotes}
            onBrowserFrameUpdate={handleBrowserFrameUpdate}
          />
        </div>
      )}

      {/* Mobile sidebar drawer */}
      {sidebarOpenMobile && (
        <>
          <div
            data-testid="mobile-sidebar-overlay"
            onClick={() => setSidebarOpenMobile(false)}
            className="md:hidden fixed inset-0 z-40"
            style={{ background: "var(--emo-overlay)", backdropFilter: "blur(4px)" }}
          />
          <div className="md:hidden fixed left-0 top-0 bottom-0 z-50 w-72 max-w-[85vw]">
            <Sidebar
              conversations={conversations}
              activeId={activeId}
              onSelect={(id) => { setActiveId(id); setSidebarOpenMobile(false); }}
              onNew={() => { handleNew(); setSidebarOpenMobile(false); }}
              onRename={handleRename}
              onDelete={handleDelete}
              user={user}
              onLogout={handleLogout}
              collapsed={false}
              onToggleCollapsed={() => setSidebarOpenMobile(false)}
              onOpenProfile={() => { setProfileOpen(true); setSidebarOpenMobile(false); }}
              mobile
            />
          </div>
        </>
      )}

      {license && (!license.active || license._showPaywall) && (
        <Paywall
          info={license}
          plans={license.plans}
          onPaid={async () => {
            const r = await http.get("/license/status");
            setLicense(r.data);
          }}
        />
      )}

      <ProfileDrawer
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
        onLogout={handleLogout}
        themeMode={themeMode}
        onThemeModeChange={setThemeMode}
        agentOnline={agentOnline}
        debugEvents={debugEvents}
        onClearDebugEvents={() => setDebugEvents([])}
      />
    </div>
  );
}
