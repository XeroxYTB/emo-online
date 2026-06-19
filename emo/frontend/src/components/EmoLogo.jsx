import React from "react";
import { Link } from "react-router-dom";

const SIZES = {
  sm: { box: 28, eye: 9, gap: 8, title: "text-sm", sub: "text-[10px]" },
  md: { box: 36, eye: 11, gap: 10, title: "text-lg", sub: "text-xs" },
  lg: { box: 44, eye: 13, gap: 12, title: "text-2xl", sub: "text-sm" },
};

function LogoMark({ size = 36, className = "" }) {
  const eye = Math.round(size * 0.3);
  const pad = Math.round(size * 0.22);
  const h = Math.round(size * 0.42);
  const r = Math.max(2, Math.round(size * 0.08));
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      aria-hidden="true"
    >
      <rect width={size} height={size} rx={r * 2} fill="var(--emo-logo-bg, #27272a)" />
      <rect x={pad} y={pad + 1} width={eye} height={h} rx={r} fill="var(--emo-accent)" />
      <rect x={size - pad - eye} y={pad + 1} width={eye} height={h} rx={r} fill="var(--emo-accent)" />
    </svg>
  );
}

export function EmoLogo({
  size = "md",
  showSubtitle = true,
  showText = true,
  subtitle = "Online",
  className = "",
  asLink = false,
  href = "/chat",
}) {
  const s = SIZES[size] || SIZES.md;
  const inner = (
    <div className={`inline-flex items-center ${className}`} style={{ gap: s.gap }}>
      <LogoMark size={s.box} />
      {showText && (
        <div className="flex items-baseline gap-1.5 leading-none">
          <span className={`font-heading font-semibold tracking-tight ${s.title}`} style={{ color: "var(--emo-text)" }}>
            Émo
          </span>
          {showSubtitle && (
            <span className={`font-normal text-muted-em ${s.sub}`}>{subtitle}</span>
          )}
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
