const BASE = '/api';

let _onUnauthorized = null;
export function setUnauthorizedHandler(fn) { _onUnauthorized = fn; }

function checkUnauth(res) {
  if (res.status === 401) {
    _onUnauthorized?.();
    throw new Error('Sesión expirada');
  }
}

function headers(token) {
  const h = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = `Bearer ${token}`;
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

export async function register(email, password, name) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) throw new Error(await parseError(res, 'Error al registrarse'));
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseError(res, 'Credenciales incorrectas'));
  return res.json();
}

export async function getMe(token) {
  const res = await fetch(`${BASE}/auth/me`, { headers: headers(token) });
  checkUnauth(res);
  if (!res.ok) throw new Error('Sin sesión');
  return res.json();
}

export async function sendChat(token, message, conversationId = null, imageBase64 = null, mode = 'nova') {
  const body = { message, mode };
  if (conversationId) body.conversation_id = conversationId;
  if (imageBase64) body.image_base64 = imageBase64;
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST', headers: headers(token), body: JSON.stringify(body),
  });
  checkUnauth(res);
  if (!res.ok) throw new Error('Error al enviar mensaje');
  return res.json();
}

export async function getConversations(token) {
  const res = await fetch(`${BASE}/conversations`, { headers: headers(token) });
  checkUnauth(res);
  if (!res.ok) return [];
  return res.json();
}

export async function getConversation(token, id) {
  const res = await fetch(`${BASE}/conversations/${id}`, { headers: headers(token) });
  checkUnauth(res);
  if (!res.ok) throw new Error('Error al cargar conversación');
  return res.json();
}

export async function deleteConversation(token, id) {
  const res = await fetch(`${BASE}/conversations/${id}`, { method: 'DELETE', headers: headers(token) });
  checkUnauth(res);
}

export async function uploadDocument(token, file, description = '') {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('description', description);
  const res = await fetch(`${BASE}/documents`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
  });
  checkUnauth(res);
  if (!res.ok) throw new Error('Error al subir documento');
  return res.json();
}

export async function getDocuments(token) {
  const res = await fetch(`${BASE}/documents`, { headers: headers(token) });
  checkUnauth(res);
  if (!res.ok) return { documents: [], total: 0 };
  return res.json();
}

export async function deleteDocument(token, id) {
  const res = await fetch(`${BASE}/documents/${id}`, { method: 'DELETE', headers: headers(token) });
  checkUnauth(res);
}

export async function sendChatWithDocument(token, file, message, conversationId, mode = 'nova') {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('message', message || '');
  fd.append('mode', mode);
  if (conversationId) fd.append('conversation_id', conversationId);
  const res = await fetch(`${BASE}/chat/document`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
  });
  checkUnauth(res);
  if (!res.ok) throw new Error(await parseError(res, 'Error al subir documento'));
  return res.json();
}

export async function interpretImage(token, imageBase64, instruction = '') {
  const res = await fetch(`${BASE}/vision/interpret`, {
    method: 'POST', headers: headers(token),
    body: JSON.stringify({ image_base64: imageBase64, instruction }),
  });
  if (!res.ok) throw new Error('Error al interpretar imagen');
  return res.json();
}
