import React from "react";

const MOOD_TO_STATE = {
  neutre: "idle",
  amusee: "happy",
  concentree: "focused",
  sarcastique: "smirk",
  ironique: "smirk",
  enthousiaste: "excited",
  agacee: "annoyed",
  curieuse: "curious",
  pensive: "thinking",
};

const MODE_DEFAULT_MOOD = {
  normal: "neutre",
  tech: "concentree",
  creatif: "enthousiaste",
  brutal: "sarcastique",
};

/** Animated SVG eyes. Inspired by the EMO robot. */
export const EmoEyes = ({ mode = "normal", mood = null, thinking = false, size = 80 }) => {
  const effectiveMood = thinking ? "thinking" : (mood || MODE_DEFAULT_MOOD[mode] || "neutre");
  const state = MOOD_TO_STATE[effectiveMood] || "idle";

  const eyeColor = "var(--mode-color)";

  // Per-state eye shape transformations
  const lidStyles = (() => {
    switch (state) {
      case "focused":
        return { top: "scaleY(0.55)", bottom: "scaleY(1)" };
      case "smirk":
        return { top: "scaleY(0.4)", bottom: "scaleY(0.7)" };
      case "annoyed":
        return { top: "scaleY(0.3)", bottom: "scaleY(1)" };
      case "happy":
        return { top: "scaleY(1)", bottom: "scaleY(0.4)" };
      case "excited":
        return { top: "scaleY(1.05)", bottom: "scaleY(1.05)" };
      case "curious":
        return { top: "scaleY(1)", bottom: "scaleY(1)" };
      case "thinking":
        return { top: "scaleY(0.7)", bottom: "scaleY(1)" };
      default:
        return { top: "scaleY(1)", bottom: "scaleY(1)" };
    }
  })();

  return (
    <div
      data-testid="emo-eyes-indicator"
      className={`mode-${mode} inline-flex items-center justify-center`}
      style={{ width: size, height: size * 0.6 }}
    >
      <svg
        viewBox="0 0 100 60"
        width={size}
        height={size * 0.6}
        style={{
          filter: `drop-shadow(0 0 ${state === "excited" ? 14 : 8}px var(--mode-glow))`,
          animation: state === "thinking" ? "pulse-glow 1.2s ease-in-out infinite" : "none",
        }}
      >
        <defs>
          <linearGradient id="eyeGrad" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor={eyeColor} stopOpacity="0.95" />
            <stop offset="1" stopColor={eyeColor} stopOpacity="0.7" />
          </linearGradient>
        </defs>
        {/* Left Eye */}
        <g
          style={{
            transformOrigin: "25px 30px",
            transform: lidStyles.top,
            animation: state === "thinking"
              ? "look-around 1.5s ease-in-out infinite"
              : "blink 5.5s infinite",
          }}
        >
          <rect x="10" y="12" width="30" height="36" rx="10" fill="url(#eyeGrad)" />
        </g>
        {/* Right Eye */}
        <g
          style={{
            transformOrigin: "75px 30px",
            transform: lidStyles.bottom,
            animation: state === "thinking"
              ? "look-around 1.5s ease-in-out infinite 0.2s"
              : "blink 5.5s infinite 0.1s",
          }}
        >
          <rect x="60" y="12" width="30" height="36" rx="10" fill="url(#eyeGrad)" />
        </g>
      </svg>
    </div>
  );
};

export default EmoEyes;
