const BASE = "/api";

let _onUnauthorized = null;
export function setUnauthorizedHandler(fn) { _onUnauthorized = fn; }

function checkUnauth(res) {
  if (res.status === 401) {
    _onUnauthorized?.();
    throw new Error("Sesión expirada");
  }
}

function headers(token) {
  const h = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function parseError(res, fallback) {
  try {
    const body = await res.json();
    return body.detail || fallback;
  } catch {
    return fallback;
  }
}

/* ── Auth — Sign in with Google ───────────────────────────────────────── */

export async function getGoogleLoginUrl() {
  const res = await fetch(`${BASE}/auth/google/login`);
  if (!res.ok) throw new Error(await parseError(res, "No se pudo iniciar sesión con Google"));
  return res.json(); // { auth_url }
}

export async function getMe(token) {
  const res = await fetch(`${BASE}/auth/me`, { headers: headers(token) });
  checkUnauth(res);
  if (!res.ok) throw new Error("Sin sesión");
  return res.json();
}

/* ── Chat ─────────────────────────────────────────────────────────────── */

/**
 * Stream a chat turn. Calls `onEvent(event)` for each SSE frame:
 * { type: "conversation" | "step" | "token" | "emotion" | "sources" | "done" | "error", ... }
 */
export async function streamChat(token, { message, conversationId, imageBase64 }, onEvent) {
  const body = { message };
  if (conversationId) body.conversation_id = conversationId;
  if (imageBase64) body.image_base64 = imageBase64;

  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST", headers: headers(token), body: JSON.stringify(body),
  });
  checkUnauth(res);
  if (!res.ok || !res.body) throw new Error("Error al enviar mensaje");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      try { onEvent(JSON.parse(line.slice(5).trim())); } catch { /* ignore partial */ }
    }
  }
}

export async function sendChatWithDocument(token, file, message, conversationId) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("message", message || "");
  if (conversationId) fd.append("conversation_id", conversationId);
  const res = await fetch(`${BASE}/chat/document`, {
    method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
  });
  checkUnauth(res);
  if (!res.ok) throw new Error(await parseError(res, "Error al subir documento"));
  return res.json();
}

/* ── Conversations ────────────────────────────────────────────────────── */

export async function getConversations(token) {
  const res = await fetch(`${BASE}/conversations`, { headers: headers(token) });
  checkUnauth(res);
  if (!res.ok) return [];
  return res.json();
}

export async function getConversation(token, id) {
  const res = await fetch(`${BASE}/conversations/${id}`, { headers: headers(token) });
  checkUnauth(res);
  if (!res.ok) throw new Error("Error al cargar conversación");
  return res.json();
}

export async function deleteConversation(token, id) {
  const res = await fetch(`${BASE}/conversations/${id}`, { method: "DELETE", headers: headers(token) });
  checkUnauth(res);
}

/* ── Documents ────────────────────────────────────────────────────────── */

export async function uploadDocument(token, file, description = "") {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("description", description);
  const res = await fetch(`${BASE}/documents`, {
    method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
  });
  checkUnauth(res);
  if (!res.ok) throw new Error("Error al subir documento");
  return res.json();
}

export async function getDocuments(token) {
  const res = await fetch(`${BASE}/documents`, { headers: headers(token) });
  checkUnauth(res);
  if (!res.ok) return { documents: [], total: 0 };
  return res.json();
}

export async function deleteDocument(token, id) {
  const res = await fetch(`${BASE}/documents/${id}`, { method: "DELETE", headers: headers(token) });
  checkUnauth(res);
}

/* ── Integrations: Google Calendar ────────────────────────────────────── */

export async function getGoogleStatus(token) {
  const res = await fetch(`${BASE}/integrations/google/status`, { headers: headers(token) });
  checkUnauth(res);
  if (!res.ok) return { configured: false, connected: false };
  return res.json();
}
