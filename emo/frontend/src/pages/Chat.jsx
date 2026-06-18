import React, { useEffect, useRef, useState, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { http, streamChat, clearSessionToken } from "../lib/api";
import { toast } from "sonner";
import { PanelRightOpen, PanelRightClose, Bug, Clock, User as UserIcon, Menu, Settings } from "lucide-react";
import Sidebar from "../components/Sidebar";
import ChatComposer from "../components/ChatComposer";
import ChatMessage from "../components/ChatMessage";
import EmoEyes from "../components/EmoEyes";
import RightPanel from "../components/RightPanel";
import AgentSettingsPanel from "../components/AgentSettingsPanel";
import Paywall from "../components/SubscriptionPlans";
import DebugWindow from "../components/DebugWindow";
import ProfileDrawer from "../components/ProfileDrawer";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../components/ui/sheet";

const MODE_TAGLINES = {
  tech: "Chirurgicale sur le code, les bugs, les systèmes.",
  creatif: "Brainstorming sans filtre. Idées audacieuses.",
  brutal: "Vérité absolue. Pas de diplomatie inutile.",
};

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
  const [allTools, setAllTools] = useState([]); // recent tools (right panel activity)
  const [rightOpen, setRightOpen] = useState(true);
  const [agentPanelOpen, setAgentPanelOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    typeof window !== "undefined" && localStorage.getItem("emo_sidebar_collapsed") === "1"
  );
  const [sidebarOpenMobile, setSidebarOpenMobile] = useState(false);
  const [debugOpen, setDebugOpen] = useState(false);
  const [debugEvents, setDebugEvents] = useState([]);
  const [license, setLicense] = useState(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [themeMode, setThemeMode] = useState(
    typeof window !== "undefined" ? (localStorage.getItem("emo_theme_mode") || "dark") : "dark"
  );
  const chatAreaRef = useRef(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("emo_sidebar_collapsed", sidebarCollapsed ? "1" : "0");
    }
  }, [sidebarCollapsed]);

  // Load preferences
  useEffect(() => {
    if (authState !== "ok") return;
    http.get("/profile").then((r) => {
      const p = r.data.preferences || {};
      if (p.theme_mode) setThemeMode(p.theme_mode);
    });
  }, [authState]);

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
        toast.success("Paiement validé. Émo est à toi à vie. 🚀");
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
    if (user) return;
    http.get("/auth/me")
      .then((res) => {
        setUser(res.data);
        setAgentOnline(!!res.data.agent_online);
        setAuthState("ok");
      })
      .catch(() => { setAuthState("no"); navigate("/login", { replace: true }); });
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

  // Auto-scroll
  useEffect(() => {
    const el = chatAreaRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, streamingMsg, streamingTools]);

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

  const handleSend = async (text) => {
    if (streaming) return;
    let convId = activeId;
    if (!convId) {
      const r = await http.post("/conversations", { title: "Nouvelle conversation", mode });
      convId = r.data.conversation_id;
      setConversations((cs) => [r.data, ...cs]);
      setActiveId(convId);
    }
    const optimistic = {
      message_id: `tmp_${Date.now()}`, role: "user", content: text, mode,
    };
    setMessages((m) => [...m, optimistic]);
    setStreaming(true);
    setStreamingMsg({ content: "" });
    setStreamingTools([]);

    let buffer = "";
    const turnTools = []; // local accumulator

    try {
      await streamChat({
        conversation_id: convId, content: text, mode,
        onEvent: (evt) => {
          pushDebug(evt);
          if (evt.type === "delta") {
            buffer += evt.content;
            const display = buffer.replace(/\[MOOD:[^\]]*\]\s*$/i, "");
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
            }
            setStreamingTools([...turnTools]);
            setAllTools((prev) => {
              const updated = [...prev];
              const idx = updated.findIndex((t) => t.id === evt.id);
              if (idx >= 0) updated[idx] = turnTools[i];
              return updated;
            });
          } else if (evt.type === "done") {
            const finalContent = buffer
              .replace(/\[MOOD:[^\]]*\]\s*$/i, "")
              .replace(/\[VERIFIED:(true|false|partial)\]\s*$/i, "")
              .replace(/\[MOOD:[^\]]*\]\s*$/i, "")
              .trim();
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
          } else if (evt.type === "info") {
            toast.info(evt.content || "Info");
          } else if (evt.type === "error") {
            toast.error("Émo : " + (evt.content || "erreur"));
            setStreamingMsg(null);
            setStreamingTools([]);
          }
        },
      });
    } catch (e) {
      toast.error("Émo : " + (e?.message || "Erreur réseau"));
      setStreamingMsg(null);
      setStreamingTools([]);
    } finally {
      setStreaming(false);
    }
  };

  if (authState === "checking") {
    return (
      <div className="h-screen w-full flex items-center justify-center">
        <EmoEyes mode="normal" thinking size={80} />
      </div>
    );
  }

  const hasMessages = messages.length > 0 || streamingMsg;
  const lastEmoMsg = [...messages].reverse().find((m) => m.role === "emo");
  const currentMood = streaming ? "thinking" : lastEmoMsg?.mood;

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

      <main className="flex-1 flex flex-col h-full relative min-w-0">
        {/* Header */}
        <header
          data-testid="chat-header"
          className="flex-shrink-0 px-3 md:px-6 py-3 flex items-center justify-between gap-2"
          style={{
            borderBottom: "1px solid var(--emo-border)",
            background: "var(--emo-glass-bg)",
            backdropFilter: "blur(20px)",
          }}
        >
          <div className="flex items-center gap-2 md:gap-3 min-w-0">
            <button
              data-testid="mobile-menu-btn"
              onClick={() => setSidebarOpenMobile(true)}
              className="md:hidden p-1.5 rounded-lg hover:bg-white/10 text-muted-em"
              aria-label="Ouvrir le menu"
            >
              <Menu size={18} />
            </button>
            <EmoEyes mode={mode} mood={currentMood} thinking={streaming} size={36} />
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="font-heading text-sm font-medium leading-none">Émo</p>
                <button
                  type="button"
                  data-testid="agent-status-pill"
                  onClick={() => setAgentPanelOpen(true)}
                  className="lg:pointer-events-none text-[9px] uppercase tracking-[0.18em] px-1.5 py-0.5 rounded-full flex items-center gap-1 cursor-pointer lg:cursor-default hover:ring-1 hover:ring-white/10 lg:hover:ring-0 transition"
                  style={{
                    background: agentOnline ? "rgba(52,211,153,0.15)" : "rgba(127,127,127,0.12)",
                    color: agentOnline ? "#34d399" : "var(--emo-text-muted)",
                  }}
                  title="Agent local — appuie pour télécharger / configurer"
                >
                  <span
                    className={`w-1 h-1 rounded-full ${agentOnline ? "bg-emerald-400" : "bg-zinc-500"}`}
                  />
                  agent {agentOnline ? "on" : "off"}
                </button>
              </div>
              <p className="hidden sm:block text-[11px] text-muted-em mt-0.5 truncate">{MODE_TAGLINES[mode]}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 md:gap-2 flex-shrink-0">
            {license && !license.active && (
              <button
                data-testid="trial-expired-pill"
                onClick={() => setLicense({ ...license, _showPaywall: true })}
                className="hidden md:inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] px-2.5 py-1 rounded-full"
                style={{ background: "rgba(239,68,68,0.12)", color: "#fca5a5", border: "1px solid rgba(239,68,68,0.3)" }}
              >
                <Clock size={10} /> essai terminé
              </button>
            )}
            {license && license.active && license.tier === "free" && !license.is_admin && (
              <span
                data-testid="trial-pill"
                className="hidden md:inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] px-2.5 py-1 rounded-full"
                style={{ background: "rgba(168,85,247,0.1)", color: "var(--mode-color)" }}
              >
                <Clock size={10} /> {license.messages_left_today}/{license.messages_per_day} · Gratuit
              </span>
            )}
            {license && license.active && license.tier && !["free"].includes(license.tier) && !license.is_admin && (
              <span
                className="hidden md:inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] px-2.5 py-1 rounded-full"
                style={{
                  background: license.tier === "ultra" ? "rgba(245,158,11,0.1)" : license.tier === "basic" ? "rgba(99,102,241,0.12)" : "rgba(52,211,153,0.1)",
                  color: license.tier === "ultra" ? "#fbbf24" : license.tier === "basic" ? "#a5b4fc" : "#34d399",
                }}
              >
                {license.tier_name}
              </span>
            )}
            {license && license.is_admin && (
              <span
                data-testid="admin-pill"
                className="hidden md:inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] px-2.5 py-1 rounded-full"
                style={{ background: "rgba(245,158,11,0.1)", color: "#fbbf24" }}
                title="Compte lifetime admin"
              >
                ∞ lifetime
              </span>
            )}
            {license?.is_admin && (
              <button
                data-testid="toggle-debug"
                onClick={() => setDebugOpen(!debugOpen)}
                className="p-2 rounded-lg hover:bg-white/10 text-muted-em hover:text-cyan-300 transition"
                title="Debug (admin)"
              >
                <Bug size={15} />
              </button>
            )}
            <button
              data-testid="header-profile-btn"
              onClick={() => setProfileOpen(true)}
              className="p-2 rounded-lg hover:bg-white/10 text-muted-em transition"
              title="Profil"
            >
              <UserIcon size={15} />
            </button>
            <button
              data-testid="mobile-agent-btn"
              onClick={() => setAgentPanelOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-white/10 text-muted-em transition"
              title="Agent local"
            >
              <Settings size={15} />
            </button>
            <button
              data-testid="toggle-right-panel"
              onClick={() => setRightOpen(!rightOpen)}
              className="hidden lg:inline-flex p-2 rounded-lg hover:bg-white/10 text-muted-em"
            >
              {rightOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
            </button>
          </div>
        </header>

        {/* Chat area */}
        <div ref={chatAreaRef} data-testid="chat-area" className="flex-1 overflow-y-auto scrollbar-thin" style={{ paddingBottom: 200 }}>
          {!hasMessages && (
            <div className="h-full flex flex-col items-center justify-center px-6 text-center">
              <EmoEyes mode={mode} mood={null} size={130} />
              <h2 className="font-heading text-3xl md:text-4xl mt-6 font-medium tracking-tight">
                Salut {(user?.name?.split(" ")[0] || "toi").replace(/^./, (c) => c.toUpperCase())}.
              </h2>
              <p className="text-secondary-em mt-2 max-w-md">
                {agentOnline ? "Agent en ligne — je peux toucher à ton PC." : "Lance ton agent local pour que je puisse coder direct chez toi."}
              </p>
            </div>
          )}

          <div className="max-w-4xl mx-auto px-4 md:px-8 pt-8 space-y-6">
            {messages.map((m) => (
              <ChatMessage key={m.message_id} message={m} />
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
              />
            )}
          </div>
        </div>

        {/* Composer */}
        <div className="absolute bottom-0 left-0 right-0 z-10 px-3 md:px-4 pb-3 md:pb-4 pt-2">
          <div className="max-w-4xl mx-auto">
            <ChatComposer
              mode={mode}
              onChangeMode={setMode}
              onSend={handleSend}
              disabled={streaming}
              showSuggestions={!hasMessages}
            />
          </div>
        </div>
      </main>

      {/* Right panel: hidden on small screens (kept for desktop only) */}
      {rightOpen && (
        <div className="hidden lg:block">
          <RightPanel
            tools={allTools}
            agentOnline={agentOnline}
            onRefreshStatus={refreshAgentStatus}
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
            style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)" }}
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

      <Sheet open={agentPanelOpen} onOpenChange={setAgentPanelOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md glass-panel border-white/10 overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="font-heading text-left">Agent local</SheetTitle>
          </SheetHeader>
          <div className="mt-4">
            <AgentSettingsPanel agentOnline={agentOnline} onRefreshStatus={refreshAgentStatus} />
          </div>
        </SheetContent>
      </Sheet>

      {debugOpen && (
        <DebugWindow
          events={debugEvents}
          onClose={() => setDebugOpen(false)}
          onClearEvents={() => setDebugEvents([])}
        />
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
        agentOnline={agentOnline}
        onPreferencesChange={(prefs) => {
          if (prefs?.theme_mode) setThemeMode(prefs.theme_mode);
        }}
      />
    </div>
  );
}
