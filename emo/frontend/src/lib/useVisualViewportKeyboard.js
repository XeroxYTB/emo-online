import { useEffect, useState } from "react";

/** Tracks soft-keyboard overlap via Visual Viewport API (iOS Safari + Android Chrome). */
export function useVisualViewportKeyboard({ enabled = true, threshold = 80 } = {}) {
  const [inset, setInset] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return undefined;
    const vv = window.visualViewport;
    if (!vv) return undefined;

    const update = () => {
      const next = Math.max(0, window.innerHeight - vv.height - vv.offsetTop);
      setInset(next);
      setOpen(next > threshold);
    };

    update();
    vv.addEventListener("resize", update);
    vv.addEventListener("scroll", update);
    return () => {
      vv.removeEventListener("resize", update);
      vv.removeEventListener("scroll", update);
    };
  }, [enabled, threshold]);

  return { inset, open };
}

export function prefersTouchKeyboard() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(pointer: coarse)").matches
    || window.matchMedia("(hover: none)").matches
    || "ontouchstart" in window
  );
}
