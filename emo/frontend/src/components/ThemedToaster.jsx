import React, { useEffect, useState } from "react";
import { Toaster } from "sonner";

function resolveToastTheme() {
  const html = document.documentElement;
  if (html.classList.contains("theme-light")) return "light";
  if (html.classList.contains("theme-dark")) return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export default function ThemedToaster() {
  const [theme, setTheme] = useState(resolveToastTheme);

  useEffect(() => {
    const sync = () => setTheme(resolveToastTheme());
    sync();
    const obs = new MutationObserver(sync);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    mq.addEventListener("change", sync);
    return () => {
      obs.disconnect();
      mq.removeEventListener("change", sync);
    };
  }, []);

  return (
    <Toaster
      theme={theme}
      position="top-right"
      toastOptions={{
        style: {
          background: "var(--emo-surface)",
          border: "1px solid var(--emo-border)",
          color: "var(--emo-text)",
          borderRadius: "var(--emo-radius-lg)",
        },
      }}
    />
  );
}
