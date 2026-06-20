import React from "react";
import { Link } from "react-router-dom";

const SIZES = {
  sm: { square: 12, gap: 4, textGap: 8, title: "text-sm", sub: "text-[10px]" },
  md: { square: 16, gap: 5, textGap: 10, title: "text-lg", sub: "text-xs" },
  lg: { square: 22, gap: 6, textGap: 12, title: "text-2xl", sub: "text-sm" },
};

function LogoMark({ square = 16, gap = 5, className = "" }) {
  const r = Math.max(3, Math.round(square * 0.32));
  const w = square * 2 + gap;
  return (
    <svg
      width={w}
      height={square}
      viewBox={`0 0 ${w} ${square}`}
      className={className}
      aria-hidden="true"
    >
      <rect width={square} height={square} rx={r} fill="var(--emo-logo-bg, #8b5cf6)" />
      <rect x={square + gap} width={square} height={square} rx={r} fill="var(--emo-logo-bg, #8b5cf6)" />
    </svg>
  );
}

export function EmoLogo({
  size = "md",
  layout = "inline",
  showSubtitle = true,
  showText = true,
  subtitle = "Online",
  className = "",
  asLink = false,
  href = "/chat",
}) {
  const s = SIZES[size] || SIZES.md;
  const stacked = layout === "stacked";

  const mark = <LogoMark square={s.square} gap={s.gap} />;
  const titleEl = showText && (
    <span
      className={`font-heading font-semibold tracking-tight ${s.title}`}
      style={{ color: "var(--emo-text)" }}
    >
      Émo
    </span>
  );
  const subtitleEl = showText && showSubtitle && (
    <span className={`font-normal text-muted-em ${s.sub}`}>{subtitle}</span>
  );

  const inner = stacked ? (
    <div className={`inline-flex flex-col items-center ${className}`} style={{ gap: s.textGap * 0.55 }}>
      {mark}
      {showText && (
        <div className="flex flex-col items-center leading-none" style={{ gap: 4 }}>
          {titleEl}
          {subtitleEl}
        </div>
      )}
    </div>
  ) : (
    <div className={`inline-flex items-center ${className}`} style={{ gap: s.textGap }}>
      {mark}
      {showText && (
        <div className="flex items-baseline gap-1.5 leading-none">
          {titleEl}
          {subtitleEl}
        </div>
      )}
    </div>
  );

  if (asLink) {
    return (
      <Link to={href} className="inline-flex no-underline hover:opacity-90 transition-opacity" data-testid="emo-logo">
        {inner}
      </Link>
    );
  }

  return <div data-testid="emo-logo">{inner}</div>;
}

export function AppTopBar({ children, className = "" }) {
  return (
    <header
      className={`app-topbar flex-shrink-0 w-full px-4 md:px-6 h-14 flex items-center justify-between border-b ${className}`}
      style={{
        borderColor: "var(--emo-border)",
        background: "var(--emo-surface)",
      }}
    >
      <EmoLogo size="sm" asLink />
      {children}
    </header>
  );
}

export default EmoLogo;
