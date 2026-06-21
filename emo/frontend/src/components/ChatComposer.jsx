import React, { useState, useRef, useEffect } from "react";
import { Send, Code, Lightbulb, Flame, ChevronDown, Cpu, Square, Bot, MessageCircle, ImagePlus, X } from "lucide-react";
import { filesToAttachments, mergeAttachments, MAX_IMAGES } from "../lib/imageAttachments";

const MODES = [
  { id: "tech", label: "Tech", Icon: Code },
  { id: "creatif", label: "Créatif", Icon: Lightbulb },
  { id: "brutal", label: "Brutal", Icon: Flame },
];

export const ChatComposer = ({
  mode, onChangeMode,
  modelPreference, onChangeModelPreference, availableModels,
  useAgentTools, onChangeUseAgentTools,
  onSend, onCancel, disabled, streaming,
}) => {
  const [value, setValue] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [openPicker, setOpenPicker] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const textareaRef = useRef(null);
  const pickerRef = useRef(null);
  const modelPickerRef = useRef(null);
  const fileInputRef = useRef(null);

  const models = availableModels?.length
    ? availableModels
    : [{ id: "auto", label: "Auto" }];

  const sortedModels = [...models].sort((a, b) => {
    if (a.id === "auto") return -1;
    if (b.id === "auto") return 1;
    if (a.uncensored && !b.uncensored) return -1;
    if (!a.uncensored && b.uncensored) return 1;
    return 0;
  });

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, [value]);

  useEffect(() => {
    if (!openPicker) return;
    const onClick = (e) => {
      const ref = openPicker === "mode" ? pickerRef : modelPickerRef;
      if (ref.current && !ref.current.contains(e.target)) setOpenPicker(null);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [openPicker]);

  const togglePicker = (id) => setOpenPicker((prev) => (prev === id ? null : id));

  const addFiles = async (files) => {
    const incoming = await filesToAttachments(files);
    if (!incoming.length) return;
    setAttachments((prev) => mergeAttachments(prev, incoming));
  };

  const submit = () => {
    const v = value.trim();
    if ((!v && !attachments.length) || disabled) return;
    onSend(v, attachments.map((a) => a.base64), attachments.map((a) => a.mediaType));
    setValue("");
    setAttachments([]);
  };

  const currentMode = MODES.find((m) => m.id === mode) || MODES[0];
  const CurrentIcon = currentMode.Icon;
  const currentModel = models.find((m) => m.id === (modelPreference || "auto")) || models[0];
  const modelShort = currentModel.id === "auto"
    ? "Auto"
    : (currentModel.label || currentModel.id).split("(")[0].trim().slice(0, 18);

  return (
    <div className={`mode-${mode} w-full`}>
      <div
        data-testid="chat-composer"
        className="emo-composer"
        data-drag={dragOver ? "true" : "false"}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          addFiles(e.dataTransfer?.files);
        }}
      >
        {/* Top toolbar: mode + model + chat/agent toggle */}
        <div className="emo-composer-toolbar">
          <div className="emo-composer-toolbar-inner">
            <div className="emo-segment emo-composer-segment" role="group" aria-label="Mode conversation">
              <button
                type="button"
                data-testid="agent-mode-toggle"
                className="emo-segment-btn"
                data-active={!useAgentTools ? "true" : "false"}
                onClick={() => onChangeUseAgentTools?.(false)}
                title="Mode chat — sans agent local"
              >
                <MessageCircle size={13} />
                <span className="hidden sm:inline">Chat</span>
              </button>
              <button
                type="button"
                className="emo-segment-btn"
                data-active={useAgentTools ? "true" : "false"}
                data-accent={useAgentTools ? "true" : "false"}
                onClick={() => onChangeUseAgentTools?.(true)}
                title="Mode agent — fichiers sur ton PC"
              >
                <Bot size={13} />
                <span className="hidden sm:inline">Agent</span>
              </button>
            </div>

            <div
              className="emo-composer-picker emo-composer-picker-mode"
              ref={pickerRef}
              data-open={openPicker === "mode" ? "true" : undefined}
            >
              <button
                type="button"
                data-testid="mode-picker-trigger"
                onClick={() => togglePicker("mode")}
                className="emo-btn-ghost emo-composer-picker-btn flex items-center gap-1.5 px-2.5 py-1.5 text-xs"
                title={currentMode.label}
                aria-expanded={openPicker === "mode"}
                aria-haspopup="listbox"
              >
                <CurrentIcon size={12} style={{ color: "var(--mode-color)" }} />
                <span className="emo-composer-picker-label">{currentMode.label}</span>
                <ChevronDown size={11} className={`transition-transform ${openPicker === "mode" ? "rotate-180" : ""}`} />
              </button>
              {openPicker === "mode" && (
                <div data-testid="mode-picker-menu" className="emo-dropdown" role="listbox">
                  {MODES.map((m) => {
                    const Icon = m.Icon;
                    const active = m.id === mode;
                    return (
                      <button
                        key={m.id}
                        data-testid={`mode-picker-${m.id}`}
                        onClick={() => {
                          onChangeMode?.(m.id);
                          setOpenPicker(null);
                        }}
                        className="emo-dropdown-item"
                        data-active={active ? "true" : "false"}
                      >
                        <Icon size={13} style={{ color: active ? "var(--mode-color)" : "var(--emo-text-muted)" }} />
                        {m.label}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div
              className="emo-composer-picker emo-composer-picker-model"
              ref={modelPickerRef}
              data-open={openPicker === "model" ? "true" : undefined}
            >
              <button
                type="button"
                data-testid="model-picker-trigger"
                onClick={() => togglePicker("model")}
                className="emo-btn-ghost emo-composer-picker-btn flex items-center gap-1.5 px-2.5 py-1.5 text-xs"
                title={currentModel.label || "Modèle"}
                aria-expanded={openPicker === "model"}
                aria-haspopup="listbox"
              >
                <Cpu size={12} />
                <span className="emo-composer-picker-label emo-composer-picker-label-model">{modelShort}</span>
                <ChevronDown size={11} className={`transition-transform ${openPicker === "model" ? "rotate-180" : ""}`} />
              </button>
              {openPicker === "model" && (
                <div data-testid="model-picker-menu" className="emo-dropdown emo-dropdown--align-end w-64" role="listbox">
                  {sortedModels.map((m) => {
                    const active = m.id === (modelPreference || "auto");
                    return (
                      <button
                        key={m.id}
                        data-testid={`model-picker-${m.id.replace(/[:/]/g, "-")}`}
                        onClick={() => {
                          onChangeModelPreference?.(m.id);
                          setOpenPicker(null);
                        }}
                        className="emo-dropdown-item"
                        data-active={active ? "true" : "false"}
                      >
                        <Cpu size={13} style={{ color: active ? "var(--emo-link)" : "var(--emo-text-muted)" }} />
                        <span className="truncate flex-1">{m.label || m.id}</span>
                        {m.uncensored && (
                          <span className="text-[9px] px-1 py-0.5 rounded flex-shrink-0 emo-alert-warning">
                            libre
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
        {attachments.length > 0 && (
          <div className="emo-attachment-strip" data-testid="composer-attachments">
            {attachments.map((a) => (
              <div key={a.preview} className="emo-attachment-chip">
                <img src={a.preview} alt={a.name || "Image"} />
                {a.name && (
                  <span className="emo-attachment-chip-name">{a.name}</span>
                )}
                <button
                  type="button"
                  onClick={() => setAttachments((prev) => prev.filter((x) => x.preview !== a.preview))}
                  className="emo-attachment-remove"
                  aria-label="Retirer l'image"
                >
                  <X size={11} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Textarea */}
        <div className="emo-composer-body">
          <textarea
            ref={textareaRef}
            data-testid="composer-textarea"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onPaste={(e) => {
              const items = e.clipboardData?.items;
              if (!items) return;
              const imageFiles = [];
              for (const item of items) {
                if (item.type.startsWith("image/")) {
                  const f = item.getAsFile();
                  if (f) imageFiles.push(f);
                }
              }
              if (imageFiles.length) {
                e.preventDefault();
                addFiles(imageFiles);
              }
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder={
              streaming
                ? "Réponse en cours…"
                : attachments.length
                  ? "Décris l'image ou pose une question…"
                  : "Écris un message — glisse ou colle une image"
            }
            disabled={disabled && !streaming}
            className="emo-composer-textarea disabled:opacity-60"
          />
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />

        {/* Footer: attach + send */}
        <div className="emo-composer-footer">
          <button
            type="button"
            data-testid="composer-image-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={attachments.length >= MAX_IMAGES || (disabled && !streaming)}
            className="emo-icon-btn"
            title={`Joindre une image (${attachments.length}/${MAX_IMAGES})`}
          >
            <ImagePlus size={15} />
          </button>

          <div className="flex items-center gap-2">
            {streaming ? (
              <button
                type="button"
                data-testid="stop-stream-btn"
                onClick={() => onCancel?.()}
                className="emo-btn-ghost flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium"
                title="Arrêter"
              >
                <Square size={13} fill="currentColor" />
                <span className="hidden sm:inline">Arrêter</span>
              </button>
            ) : (
              <button
                data-testid="send-message-btn"
                onClick={submit}
                disabled={disabled || (!value.trim() && !attachments.length)}
                className="emo-send-btn"
                title="Envoyer"
              >
                <Send size={15} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatComposer;
