/** Strip MOOD tags, tool-call leaks, and other LLM artefacts from displayed text. */
export function cleanDisplayText(text) {
  if (!text) return "";
  return text
    .replace(/<function\s*\([^)]*\)\s*\{[\s\S]*?\}\s*(?:<\/function>)?/gi, "")
    .replace(/<function[^>]*>[\s\S]*?<\/function>/gi, "")
    .replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, "")
    .replace(/\[(?:MOOD|VERIFIED|TOOL):[^\]]*\]/gi, "")
    .replace(/<MOOD:[^>]*>/gi, "")
    .replace(/^(?:Slt\s*)?Émo\s*[A-Za-zéèê]+\s*/i, "")
    .replace(/^\s*Émo\s*/i, "")
    .trim();
}