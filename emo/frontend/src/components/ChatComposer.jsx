import React, { useState, useRef, useEffect } from "react";
import { Send, Code, Lightbulb, Flame, ChevronDown, Cpu, Square, Bot, MessageCircle } from "lucide-react";

const MODES = [
  { id: "tech", label: "Tech", Icon: Code, hint: "Code, debug, systèmes" },
  { id: "creatif", label: "Créatif", Icon: Lightbulb, hint: "Brainstorming et idées" },
  { id: "brutal", label: "Brutal", Icon: Flame, hint: "Feedback sans filtre" },
];

const QUICK_SUGGESTIONS = {
  tech: [
    "Crée un mini-projet de A à Z",
    "Trouve la doc officielle et résume",
    "Propose une architecture pour ma feature",
  ],
  creatif: [
    "10 idées de projets perso",
    "Trouve un nom pour mon projet",
    "Concepts visuels originaux",
  ],
  brutal: [
    "Mon idée tient-elle la route ?",
    "Pourquoi je procrastine ?",
    "Critique honnête de mon dernier choix",
  ],
};

export const ChatComposer = ({
  mode, onChangeMode,
  modelPreference, onChangeModelPreference, availableModels,
  useAgentTools, onChangeUseAgentTools,
  onSend, onCancel, disabled, streaming, showSuggestions,
}) => {
  const [value, setValue] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [modelPickerOpen, setModelPickerOpen] = useState(false);
  const textareaRef = useRef(null);
  const pickerRef = useRef(null);
  const modelPickerRef = useRef(null);

  const models = availableModels?.length
    ? availableModels
    : [{ id: "auto", label: "Auto (meilleur modèle disponible)" }];

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, [value]);

  useEffect(() => {
    if (!pickerOpen && !modelPickerOpen) return;
    const onClick = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) setPickerOpen(false);
      if (modelPickerRef.current && !modelPickerRef.current.contains(e.target)) setModelPickerOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [pickerOpen, modelPickerOpen]);

  const submit = () => {
    const v = value.trim();
    if (!v || disabled) return;
    onSend(v);
    setValue("");
  };

  const currentMode = MODES.find((m) => m.id === mode) || MODES[0];
  const CurrentIcon = currentMode.Icon;
  const currentModel = models.find((m) => m.id === (modelPreference || "auto")) || models[0];
  const modelShort = currentModel.id === "auto"
    ? "Auto"
    : (currentModel.label || currentModel.id).split("(")[0].trim().slice(0, 18);

  return (
    <div className={`mode-${mode} w-full`}>
      {showSuggestions && (
        <div data-testid="quick-suggestions" className="flex flex-wrap gap-2 mb-3 justify-center">
          {(QUICK_SUGGESTIONS[mode] || QUICK_SUGGESTIONS.tech).map((s) => (
            <button
              key={s}
              data-testid={`suggestion-${s.slice(0, 20)}`}
              onClick={() => onSend(s)}
              disabled={disabled}
              className="text-xs px-3 py-1.5 rounded-lg border text-secondary-em hover:text-white hover:border-white/20 transition-colors"
              style={{ borderColor: "var(--emo-border)", background: "var(--emo-surface)" }}
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <div
        data-testid="chat-composer"
        className="rounded-xl p-2 flex flex-col gap-1 transition-colors"
        style={{
          background: "var(--emo-surface)",
          border: "1px solid var(--emo-border)",
        }}
      >
        <textarea
          ref={textareaRef}
          data-testid="composer-textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={1}
          placeholder={streaming ? "Émo répond… (Échap ou Arrêter pour interrompre)" : "Écris ton message…"}
          disabled={disabled && !streaming}
          className="w-full bg-transparent border-none focus:outline-none focus:ring-0 resize-none py-3 px-3 text-base placeholder:text-muted-em disabled:opacity-60"
          style={{ maxHeight: 180, color: "var(--emo-text)" }}
        />
        <div className="flex items-center justify-between gap-2 px-2 pb-1">
          <div className="flex items-center gap-1.5 flex-wrap">
          <div className="relative" ref={pickerRef}>
            <button
              type="button"
              data-testid="mode-picker-trigger"
              onClick={() => setPickerOpen((o) => !o)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition border"
              style={{
                background: "var(--emo-surface-raised)",
                borderColor: "var(--emo-border)",
                color: "var(--emo-text-secondary)",
              }}
              title={currentMode.hint}
            >
              <CurrentIcon size={12} />
              <span className="hidden sm:inline">{currentMode.label}</span>
              <ChevronDown size={11} className={`transition-transform ${pickerOpen ? "rotate-180" : ""}`} />
            </button>
            {pickerOpen && (
              <div
                data-testid="mode-picker-menu"
                className="absolute bottom-full left-0 mb-2 w-56 rounded-lg py-1 z-30 border"
                style={{ background: "var(--emo-surface)", borderColor: "var(--emo-border)" }}
              >
                {MODES.map((m) => {
                  const Icon = m.Icon;
                  const active = m.id === mode;
                  return (
                    <button
                      key={m.id}
                      data-testid={`mode-picker-${m.id}`}
                      onClick={() => {
                        onChangeMode?.(m.id);
                        setPickerOpen(false);
                      }}
                      className={`w-full flex items-start gap-2.5 px-3 py-2 text-left text-xs transition ${active ? "bg-white/5" : "hover:bg-white/[0.04]"}`}
                    >
                      <Icon size={13} className="mt-0.5 flex-shrink-0" style={{ color: active ? "var(--mode-color)" : "var(--emo-text-secondary)" }} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium" style={{ color: active ? "var(--emo-text)" : "var(--emo-text-secondary)" }}>{m.label}</p>
                        <p className="text-[10px] mt-0.5 text-muted-em">{m.hint}</p>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
          <div className="relative" ref={modelPickerRef}>
            <button
              type="button"
              data-testid="model-picker-trigger"
              onClick={() => setModelPickerOpen((o) => !o)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition border"
              style={{
                background: "var(--emo-surface-raised)",
                borderColor: "var(--emo-border)",
                color: "var(--emo-text-secondary)",
              }}
              title={currentModel.label || "Modèle IA"}
            >
              <Cpu size={12} />
              <span className="hidden sm:inline max-w-[120px] truncate">{modelShort}</span>
              <ChevronDown size={11} className={`transition-transform ${modelPickerOpen ? "rotate-180" : ""}`} />
            </button>
            {modelPickerOpen && (
              <div
                data-testid="model-picker-menu"
                className="absolute bottom-full left-0 mb-2 w-64 max-h-64 overflow-y-auto rounded-lg py-1 z-30 border scrollbar-thin"
                style={{ background: "var(--emo-surface)", borderColor: "var(--emo-border)" }}
              >
                {models.map((m) => {
                  const active = m.id === (modelPreference || "auto");
                  return (
                    <button
                      key={m.id}
                      data-testid={`model-picker-${m.id.replace(/[:/]/g, "-")}`}
                      onClick={() => {
                        onChangeModelPreference?.(m.id);
                        setModelPickerOpen(false);
                      }}
                      className={`w-full flex items-start gap-2 px-3 py-2 text-left text-xs transition ${active ? "bg-white/5" : "hover:bg-white/[0.04]"}`}
                    >
                      <Cpu size={13} className="mt-0.5 flex-shrink-0" style={{ color: active ? "#93c5fd" : "var(--emo-text-secondary)" }} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate" style={{ color: active ? "var(--emo-text)" : "var(--emo-text-secondary)" }}>
                          {m.label || m.id}
                        </p>
                        {m.id === "auto" && (
                          <p className="text-[10px] mt-0.5 text-muted-em">Choisit le meilleur modèle, bascule si besoin</p>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
          <button
            type="button"
            data-testid="agent-mode-toggle"
            onClick={() => onChangeUseAgentTools?.(!useAgentTools)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition border"
            style={{
              background: useAgentTools ? "var(--emo-surface-raised)" : "transparent",
              borderColor: useAgentTools ? "var(--emo-accent)" : "var(--emo-border)",
              color: useAgentTools ? "var(--emo-text)" : "var(--emo-text-muted)",
            }}
            title={useAgentTools ? "Mode Agent — tools actifs (Cursor/Claude)" : "Mode Chat — réponse directe sans tools"}
          >
            {useAgentTools ? <Bot size={12} /> : <MessageCircle size={12} />}
            <span className="hidden sm:inline">{useAgentTools ? "Agent" : "Chat"}</span>
          </button>
          </div>
          {streaming ? (
            <button
              type="button"
              data-testid="stop-stream-btn"
              onClick={() => onCancel?.()}
              className="h-9 px-3 flex-shrink-0 flex items-center justify-center gap-1.5 rounded-lg transition-colors text-xs font-medium border"
              style={{
                background: "transparent",
                borderColor: "var(--emo-border)",
                color: "var(--emo-text-secondary)",
              }}
              title="Arrêter la réponse"
            >
              <Square size={14} fill="currentColor" />
              <span className="hidden sm:inline">Arrêter</span>
            </button>
          ) : (
            <button
              data-testid="send-message-btn"
              onClick={submit}
              disabled={disabled || !value.trim()}
              className="h-9 w-9 flex-shrink-0 flex items-center justify-center rounded-lg transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
              style={{
                background: "var(--emo-accent)",
                color: "#fff",
              }}
            >
              <Send size={15} />
            </button>
          )}
        </div>
      </div>
      <p className="hidden sm:block text-[11px] text-muted-em text-center mt-2">
        Entrée pour envoyer · Maj+Entrée pour un saut de ligne
      </p>
    </div>
  );
};

export default ChatComposer;
