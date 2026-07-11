import React, { useEffect, useRef, useState, useCallback } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { http, streamChat, clearSessionToken, wakeBackend, getSessionToken } from "../lib/api";
import { toast } from "sonner";
import { PanelRightOpen, PanelRightClose, Clock, User as UserIcon, Menu, ArrowDown, Wifi, RefreshCw, Loader2 } from "lucide-react";
import Sidebar from "../components/Sidebar";
import ChatComposer from "../components/ChatComposer";
import ChatMessage from "../components/ChatMessage";
import EmoEyes from "../components/EmoEyes";
import { AppTopBar } from "../components/EmoLogo";
import RightPanel from "../components/RightPanel";
import Paywall from "../components/SubscriptionPlans";
import ProfileDrawer from "../components/ProfileDrawer";
import FeedbackPrompt from "../components/FeedbackPrompt";
import { cleanDisplayText } from "../lib/messageClean";
import { isHtmlPath, normalizeFilePath } from "../lib/filePreview";
import { buildImagePreviewSrc } from "../lib/resolveToolPreview";
import { useVisualViewportKeyboard } from "../lib/useVisualViewportKeyboard";

const MODE_LABELS = { tech: "Tech", creatif: "Créatif", brutal: "Brutal" };

function cleanStreamText(text) {
  return cleanDisplayText(text);
}

function StatusScreen({ icon: Icon, title, description, action, actionLabel, loading }) {
  return (
    <div className="login-page h-screen w-full flex flex-col">
      <AppTopBar />
      <div className="emo-status-screen flex-1">
        <div className="emo-status-card">
          <div className="emo-status-icon">
            {loading ? <Loader2 size={22} className="animate-spin" /> : <Icon size={22} />}
          </div>
          <h2 className="font-heading text-base font-semibold mb-2" style={{ color: "var(--emo-text)" }}>
            {title}
          </h2>
          <p className="text-sm text-secondary-em mb-5">{description}</p>
          {action && (
            <button
              type="button"
              onClick={action}
              className="emo-btn-primary w-full py-2.5 text-sm flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
              {actionLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Chat() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(location.state?.user || null);
  const [authState, setAuthState] = useState(location.state?.user ? "ok" : "checking");
  const [retryLoading, setRetryLoading] = useState(false);

  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [mode, setMode] = useState("tech");
  const [streaming, setStreaming] = useState(false);
  const [streamingMsg, setStreamingMsg] = useState(null);
  const [streamingTools, setStreamingTools] = useState([]);
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
  const [rightOpen, setRightOpen] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("emo_right_panel_open") === "1";
  });
  const [rightPanelMobileOpen, setRightPanelMobileOpen] = useState(false);
  const [debugEvents, setDebugEvents] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    typeof window !== "undefined" && localStorage.getItem("emo_sidebar_collapsed") === "1"
  );
  const [sidebarOpenMobile, setSidebarOpenMobile] = useState(false);
  const [license, setLicense] = useState(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileSection, setProfileSection] = useState("profile");
  const [searchParams, setSearchParams] = useSearchParams();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [themeMode, setThemeMode] = useState(
    typeof window !== "undefined" ? (localStorage.getItem("emo_theme_mode") || "dark") : "dark"
  );
  const [modelPreference, setModelPreference] = useState(
    typeof window !== "undefined" ? (localStorage.getItem("emo_model_preference") || "auto") : "auto"
  );
  const [useAgentTools, setUseAgentTools] = useState(
    typeof window !== "undefined" ? localStorage.getItem("emo_use_agent_tools") !== "0" : true
  );
  const [agentProjectPath, setAgentProjectPath] = useState(
    () => (typeof window !== "undefined" ? localStorage.getItem("emo_agent_project_path") || "" : "")
  );
  const [agentStatus, setAgentStatus] = useState("");
  const [availableModels, setAvailableModels] = useState([{ id: "auto", label: "Auto" }]);
  const chatAreaRef = useRef(null);
  const stickyBottomRef = useRef(true);
  const streamAbortRef = useRef(null);
  const themeSyncedRef = useRef(false);
  const [mobileLayout, setMobileLayout] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches,
  );
  const { inset: mobileKbInset, open: mobileKeyboardOpen } = useVisualViewportKeyboard({
    enabled: mobileLayout,
  });
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

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("emo_right_panel_open", rightOpen ? "1" : "0");
    }
  }, [rightOpen]);

  useEffect(() => {
    const locked = sidebarOpenMobile || profileOpen || rightPanelMobileOpen;
    document.body.classList.toggle("emo-scroll-locked", locked);
    return () => document.body.classList.remove("emo-scroll-locked");
  }, [sidebarOpenMobile, profileOpen, rightPanelMobileOpen]);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const onChange = () => setMobileLayout(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty("--emo-mobile-kb-inset", `${mobileKbInset}px`);
    document.body.classList.toggle("emo-mobile-keyboard-open", mobileKeyboardOpen);
    return () => {
      document.documentElement.style.removeProperty("--emo-mobile-kb-inset");
      document.body.classList.remove("emo-mobile-keyboard-open");
    };
  }, [mobileKbInset, mobileKeyboardOpen]);

  useEffect(() => {
    document.body.classList.toggle("emo-browser-sheet-open", rightPanelMobileOpen);
    return () => document.body.classList.remove("emo-browser-sheet-open");
  }, [rightPanelMobileOpen]);

  useEffect(() => {
    if (!sidebarOpenMobile) return;
    const onKey = (e) => {
      if (e.key === "Escape") setSidebarOpenMobile(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarOpenMobile]);

  useEffect(() => {
    if (!rightPanelMobileOpen) return;
    const onKey = (e) => {
      if (e.key === "Escape") setRightPanelMobileOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [rightPanelMobileOpen]);

  useEffect(() => {
    const settings = searchParams.get("settings");
    if (settings === "connections") {
      setProfileSection("connections");
      setProfileOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete("settings");
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (!profileOpen) return;
    const onKey = (e) => {
      if (e.key === "Escape") setProfileOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [profileOpen]);

  const openProfile = () => {
    setSidebarOpenMobile(false);
    setRightPanelMobileOpen(false);
    setProfileSection("profile");
    setProfileOpen(true);
  };

  const openSidebarMobile = () => {
    setProfileOpen(false);
    setRightPanelMobileOpen(false);
    setSidebarOpenMobile(true);
  };

  const toggleRightPanel = () => {
    if (typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches) {
      setRightPanelMobileOpen((open) => {
        if (open) return false;
        setSidebarOpenMobile(false);
        setProfileOpen(false);
        return true;
      });
    } else {
      setRightOpen((o) => !o);
    }
  };

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

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("emo_agent_project_path", agentProjectPath || "");
    }
  }, [agentProjectPath]);

  useEffect(() => {
    const html = document.documentElement;
    const apply = (modeVal) => {
      let resolved = modeVal;
      if (modeVal === "system") {
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

  useEffect(() => {
    if (authState !== "ok") return;
    const tick = async () => {
      try {
        const r = await http.get("/license/status");
        setLicense(r.data);
      } catch { /* ignore */ }
    };
    tick();
    const params = new URLSearchParams(window.location.search);
    const sid = params.get("stripe_session_id");
    if (sid) {
      pollPayment(sid);
      window.history.replaceState({}, document.title, "/chat");
    }
  }, [authState]);

  useEffect(() => {
    if (authState !== "ok") return;
    http.get("/feedback/eligible")
      .then((r) => {
        if (r.data?.eligible) {
          setFeedbackOpen(true);
          http.post("/feedback/shown").catch(() => {});
        }
      })
      .catch(() => {});
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

  useEffect(() => {
    if (user) {
      setAuthState("ok");
      return undefined;
    }
    let cancelled = false;
    const timeoutId = setTimeout(() => {
      if (!cancelled) setAuthState("timeout");
    }, getSessionToken() ? 12000 : 8000);
    http.get("/auth/me", { timeout: 6000, _emoSkipRetry: true, _emoMaxRetries: 0 })
      .then((res) => {
        if (cancelled) return;
        setUser(res.data);
        setAgentOnline(!!res.data.agent_online);
        setAuthState("ok");
      })
      .catch(() => {
        if (!cancelled) {
          clearSessionToken();
          setAuthState("no");
          navigate("/login", { replace: true });
        }
      })
      .finally(() => clearTimeout(timeoutId));
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [user, navigate]);

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

  useEffect(() => {
    if (authState !== "ok") return;
    http.get("/conversations").then((r) => {
      setConversations(r.data);
      if (r.data.length > 0 && !activeId) setActiveId(r.data[0].conversation_id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authState]);

  useEffect(() => {
    if (!activeId) { setMessages([]); return; }
    http.get(`/conversations/${activeId}/messages`).then((r) => setMessages(r.data));
    const c = conversations.find((cv) => cv.conversation_id === activeId);
    if (c?.mode) setMode(c.mode);
    if (c?.agent_project_path) setAgentProjectPath(c.agent_project_path);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

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
          "browser_click", "browser_snapshot", "browser_scroll", "browser_press", "browser_type", "browser_fill",
        ].includes(updated[i].tool)) {
          idx = i;
          break;
        }
      }
    } else if (preview.type === "image") {
      let matched = false;
      if (preview.toolId) {
        const match = updated.findIndex((t) => t.id === preview.toolId);
        if (match >= 0) {
          idx = match;
          matched = true;
        }
      }
      if (!matched) {
        for (let i = updated.length - 1; i >= 0; i -= 1) {
          if (updated[i].tool === "generate_image") {
            idx = i;
            break;
          }
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
    setAgentStatus("");

    let buffer = "";
    const turnTools = [];
    const abortController = new AbortController();
    streamAbortRef.current = abortController;
    const streamTimeoutRef = { id: null };
    const resetStreamTimeout = () => {
      if (streamTimeoutRef.id) clearTimeout(streamTimeoutRef.id);
      const ms = useAgentTools ? 30 * 60 * 1000 : 3 * 60 * 1000;
      streamTimeoutRef.id = setTimeout(() => {
        abortController.abort();
        toast.error(useAgentTools ? "Délai agent dépassé (30 min)." : "Délai dépassé.");
      }, ms);
    };
    resetStreamTimeout();

    try {
      await streamChat({
        conversation_id: convId, content: text, images,
        image_media_types: imageMediaTypes.length ? imageMediaTypes : undefined,
        mode,
        model_preference: modelPreference || "auto",
        use_agent_tools: useAgentTools,
        agent_project_path: agentProjectPath,
        signal: abortController.signal,
        onEvent: (evt) => {
          if (["delta", "ping", "tool_start", "tool_executing", "tool_result", "agent_status"].includes(evt.type)) {
            resetStreamTimeout();
          }
          pushDebug(evt);
          if (evt.type === "agent_status") {
            setAgentStatus(evt.message || "");
          } else if (evt.type === "delta") {
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
                } else if (tool === "generate_image" && evt.result?.ok !== false) {
                  if (evt.result?.image_url || evt.result?.image_base64 || evt.result?.has_image) {
                    turnTools[i].inlinePreview = {
                      type: "image",
                      image_url: evt.result.image_url,
                      image_base64: evt.result.image_base64,
                      mime: evt.result.mime || "image/png",
                      title: args.prompt || evt.result.prompt || evt.result.subject || "Image générée",
                      has_image: evt.result.has_image,
                    };
                  }
                } else if (BROWSER_PREVIEW_TOOLS.includes(tool)) {
                  const bp = buildBrowserPreview(tool, args, evt.result);
                  if (bp) {
                    turnTools[i].inlinePreview = bp;
                    setBrowserFrames((prev) => {
                      const sid = bp.session_id || "default";
                      const url = bp.url || "";
                      const idx = prev.findIndex(
                        (f) => f.session_id === sid || (url && f.url === url),
                      );
                      const id =
                        idx >= 0
                          ? prev[idx].id
                          : `bf_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
                      const nextFrame = { id, action: "control", ...bp };
                      if (idx >= 0) {
                        const updated = [...prev];
                        updated[idx] = { ...updated[idx], ...nextFrame };
                        return updated;
                      }
                      return [nextFrame, ...prev].slice(0, 24);
                    });
                  }
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
            if (!evt.image_url && !evt.image_base64 && !evt.has_image) return;
            const preview = {
              type: "image",
              image_url: evt.image_url,
              image_base64: evt.image_base64,
              mime: evt.mime || "image/png",
              title: evt.title || "Image générée",
              toolId: evt.id,
              has_image: evt.has_image,
            };
            const i = evt.id ? turnTools.findIndex((t) => t.id === evt.id) : -1;
            if (i >= 0) {
              turnTools[i].inlinePreview = preview;
              if (turnTools[i].state !== "error") turnTools[i].state = "done";
            } else {
              const updated = attachInlinePreview(turnTools, preview);
              turnTools.splice(0, turnTools.length, ...updated);
            }
            setStreamingTools([...turnTools]);
            setAllTools((prev) => {
              const updated = [...prev];
              const idx = evt.id ? updated.findIndex((t) => t.id === evt.id) : -1;
              if (idx >= 0) {
                updated[idx] = {
                  ...updated[idx],
                  inlinePreview: preview,
                  state: updated[idx].state === "error" ? "error" : "done",
                };
              }
              return updated;
            });
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
              if (typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches) {
                setRightPanelMobileOpen(true);
              }
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
            // keepalive
          } else if (evt.type === "error") {
            const errText = evt.content || "Erreur.";
            toast.error(errText);
            setMessages((m) => [
              ...m,
              {
                message_id: `err_${Date.now()}`,
                role: "emo",
                content: errText,
                mode,
                mood: "neutre",
              },
            ]);
            setStreamingMsg(null);
            setStreamingTools([]);
          } else if (evt.type === "cancelled") {
            setStreamingMsg(null);
            setStreamingTools([]);
          } else if (evt.type === "auth_error") {
            // Session invalide : on sort de l'état de streaming et on renvoie au login.
            setStreamingMsg(null);
            setStreamingTools([]);
            setUser(null);
            setAuthState("expired");
            toast.error("Session expirée. Veuillez vous reconnecter.");
            setTimeout(() => navigate("/login", { replace: true }), 800);
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
      if (streamTimeoutRef.id) clearTimeout(streamTimeoutRef.id);
      if (streamAbortRef.current === abortController) {
        streamAbortRef.current = null;
      }
      setStreaming(false);
      setAgentStatus("");
    }
  };

  const handleAuthRetry = async () => {
    setRetryLoading(true);
    setAuthState("checking");
    try {
      await wakeBackend({ maxWaitMs: 30000 });
      const res = await http.get("/auth/me", { timeout: 8000, _emoSkipRetry: true, _emoMaxRetries: 0 });
      setUser(res.data);
      setAgentOnline(!!res.data.agent_online);
      setAuthState("ok");
    } catch {
      navigate("/login", { replace: true });
    } finally {
      setRetryLoading(false);
    }
  };

  if (authState === "checking") {
    return (
      <StatusScreen
        icon={Loader2}
        title="Connexion en cours"
        description="Vérification de votre session…"
        loading
      />
    );
  }

  if (authState === "timeout") {
    return (
      <StatusScreen
        icon={Wifi}
        title="Connexion lente"
        description="Le serveur démarre peut‑être. Patientez un instant puis réessayez."
        action={handleAuthRetry}
        actionLabel="Réessayer"
        loading={retryLoading}
      />
    );
  }

  const hasMessages = messages.length > 0 || streamingMsg;
  const activeConv = conversations.find((c) => c.conversation_id === activeId);

  return (
    <div
      className={`mode-${mode} emo-app-shell`}
      data-right-panel-open={rightOpen && !mobileLayout ? "true" : "false"}
    >
      {!mobileLayout && (
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
          onOpenProfile={openProfile}
        />
      )}

      <main className="emo-chat-main">
        <header data-testid="chat-header" className="emo-chat-header">
          <div className="flex items-center gap-2 md:gap-3 min-w-0">
            <button
              data-testid="mobile-menu-btn"
              onClick={openSidebarMobile}
              className="md:hidden emo-icon-btn"
              aria-label="Ouvrir le menu"
            >
              <Menu size={17} />
            </button>
            <div className="min-w-0">
              <p className="font-heading text-sm font-semibold truncate leading-tight">
                {activeConv?.title || "Nouvelle conversation"}
              </p>
              <p className="emo-chat-header-subtitle text-[11px] text-muted-em truncate">
                Mode {MODE_LABELS[mode] || mode}
                {useAgentTools ? " · Agent" : " · Chat"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1 flex-shrink-0">
            {license && license.active && license.tier === "free" && !license.is_admin && (
              <span
                data-testid="trial-pill"
                className="hidden sm:inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wide px-2.5 py-1 rounded-full font-medium"
                style={{ background: "var(--emo-accent-soft)", color: "var(--mode-color)" }}
              >
                <Clock size={10} />
                {license.messages_left_today}/{license.messages_per_day}
              </span>
            )}
            <button
              data-testid="toggle-right-panel"
              onClick={toggleRightPanel}
              className="emo-icon-btn"
              title={rightOpen || rightPanelMobileOpen ? "Masquer le panneau" : "Afficher le panneau"}
            >
              {(rightOpen || rightPanelMobileOpen) ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
            </button>
            <button
              data-testid="header-profile-btn"
              onClick={openProfile}
              className="emo-icon-btn"
              title="Paramètres"
            >
              <UserIcon size={15} />
            </button>
          </div>
        </header>

        <div className="flex-1 min-h-0 relative flex flex-col">
          <div
            ref={chatAreaRef}
            data-testid="chat-area"
            className="emo-chat-scroll chat-scroll-area scrollbar-thin"
          >
            {!hasMessages && (
              <div className="h-full min-h-[320px] flex flex-col items-center justify-center px-6 gap-4">
                <EmoEyes mode={mode} mood={null} size={120} />
                <div className="text-center max-w-sm">
                  <p className="font-heading text-base font-semibold mb-1" style={{ color: "var(--emo-text)" }}>
                    Bonjour{user?.name ? `, ${user.name.split(" ")[0]}` : ""}
                  </p>
                  <p className="text-sm text-muted-em">
                    Pose une question, joins une image, ou laisse l'agent explorer le web.
                  </p>
                </div>
              </div>
            )}

            {hasMessages && (
              <div className="emo-chat-messages">
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
            )}
          </div>

          {showScrollBtn && (
            <button
              type="button"
              onClick={() => scrollToBottom("smooth")}
              className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-medium transition hover:scale-105"
              style={{
                background: "var(--emo-surface)",
                border: "1px solid var(--emo-border)",
                color: "var(--emo-text-secondary)",
                boxShadow: "var(--emo-shadow-lg)",
              }}
              aria-label="Revenir en bas"
            >
              <ArrowDown size={14} />
              {streaming ? "En cours…" : "Bas de page"}
            </button>
          )}
        </div>

        <div className="emo-chat-composer-wrap">
          <div className="emo-chat-composer-inner">
            <ChatComposer
              mode={mode}
              onChangeMode={setMode}
              modelPreference={modelPreference}
              onChangeModelPreference={setModelPreference}
              availableModels={availableModels}
              useAgentTools={useAgentTools}
              onChangeUseAgentTools={setUseAgentTools}
              agentProjectPath={agentProjectPath}
              onChangeAgentProjectPath={setAgentProjectPath}
              agentStatus={agentStatus}
              onSend={handleSend}
              onCancel={handleCancel}
              disabled={false}
              streaming={streaming}
            />
          </div>
        </div>
      </main>

      {rightOpen && (
        <div className="hidden md:flex flex-shrink-0 emo-right-panel-wrap">
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

      {rightPanelMobileOpen && (
        <>
          <div
            data-testid="mobile-right-panel-overlay"
            onClick={() => setRightPanelMobileOpen(false)}
            className="md:hidden emo-drawer-overlay"
          />
          <div className="md:hidden emo-bottom-sheet" role="dialog" aria-label="Panneau activité">
            <div className="emo-bottom-sheet-handle" aria-hidden />
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
              mobileSheet
              onClose={() => setRightPanelMobileOpen(false)}
            />
          </div>
        </>
      )}

      {sidebarOpenMobile && (
        <>
          <div
            data-testid="mobile-sidebar-overlay"
            onClick={() => setSidebarOpenMobile(false)}
            className="md:hidden emo-drawer-overlay emo-sidebar-drawer-overlay"
          />
          <div className="md:hidden emo-sidebar-drawer">
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
              onOpenProfile={() => { openProfile(); setSidebarOpenMobile(false); }}
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
        initialSection={profileSection}
        onLogout={handleLogout}
        themeMode={themeMode}
        onThemeModeChange={setThemeMode}
        agentOnline={agentOnline}
        debugEvents={debugEvents}
        onClearDebugEvents={() => setDebugEvents([])}
      />

      <FeedbackPrompt open={feedbackOpen} onClose={() => setFeedbackOpen(false)} />
    </div>
  );
}
