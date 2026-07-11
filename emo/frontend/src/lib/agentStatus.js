/** Parse /agent/status ou /auth/me — source unique pour l'état desktop. */
export function parseAgentStatus(data) {
  const desktopOnline = Boolean(data?.desktop_online);
  const agentToolsOnline = Boolean(data?.online ?? data?.agent_online);
  const desktopLinked = Boolean(data?.desktop_linked);
  const connected = desktopOnline || agentToolsOnline;
  return { desktopOnline, agentToolsOnline, desktopLinked, connected };
}
