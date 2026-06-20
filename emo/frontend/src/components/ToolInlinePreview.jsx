import React from "react";
import ChatPreviewBubble from "./ChatPreviewBubble";
import { hasToolPreview } from "../lib/resolveToolPreview";

/** @deprecated Utiliser ChatPreviewBubble — conservé pour compat. */
export function ToolInlinePreview({ event }) {
  if (!hasToolPreview(event)) return null;
  return <ChatPreviewBubble event={event} className="mt-2" />;
}

export default ToolInlinePreview;
