"use strict";

// A small client for the REST API: the same endpoints a mobile app would use.
//   POST /api/auth/login/    -> {access, refresh}
//   POST /api/auth/refresh/  -> {access}, a new access token without the password
//   GET  /api/auth/me/       -> who is logged in
//   POST /api/chat/          -> the assistant's reply, given the whole conversation

// sessionStorage lives only as long as this browser tab (unlike localStorage).
const ACCESS_KEY = "muni.accessToken";
const REFRESH_KEY = "muni.refreshToken";

const TOOL_LABELS = {
  search_procedures: "Buscó trámites",
  get_procedure_details: "Revisó requisitos",
  list_my_complaints: "Consultó tus reclamos",
  get_complaint_status: "Consultó un reclamo",
};

const state = {
  access: null,
  refresh: null,
  user: null,
  // The conversation as plain text turns. The server keeps nothing between
  // requests, so the whole history goes with every message.
  history: [],
  busy: false,
};

const $ = (id) => document.getElementById(id);

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function api(path, { method = "GET", body, retry = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.access) headers.Authorization = `Bearer ${state.access}`;

  let response;
  try {
    response = await fetch(path, { method, headers, body: body && JSON.stringify(body) });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor.");
  }

  // The access token lasts an hour. When it expires, get a new one with the
  // refresh token and repeat the request once, so the person stays logged in.
  if (response.status === 401 && retry && state.refresh && (await refreshAccessToken())) {
    return api(path, { method, body, retry: false });
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, data.detail || `Error ${response.status}`);
  return data;
}

async function refreshAccessToken() {
  try {
    const response = await fetch("/api/auth/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: state.refresh }),
    });
    if (!response.ok) return false; // the refresh token expired too: log in again
    state.access = (await response.json()).access;
    saveTokens();
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------- session

async function start() {
  readTokens();
  if (!state.access) return showLogin();
  try {
    state.user = await api("/api/auth/me/");
    showChat();
  } catch {
    logout(); // both tokens expired, or invalid
  }
}

async function login(event) {
  event.preventDefault();
  const email = $("email").value.trim();
  const password = $("password").value;
  if (!email || !password) return showLoginError("Ingresa tu correo y tu contraseña.");

  $("login-button").disabled = true;
  try {
    const tokens = await api("/api/auth/login/", { method: "POST", body: { email, password }, retry: false });
    state.access = tokens.access;
    state.refresh = tokens.refresh;
    saveTokens();
    state.user = await api("/api/auth/me/");
    $("password").value = "";
    showChat();
  } catch (error) {
    showLoginError(error.status === 401 ? "Correo o contraseña incorrectos." : error.message);
  } finally {
    $("login-button").disabled = false;
  }
}

function logout(message) {
  state.access = null;
  state.refresh = null;
  state.user = null;
  saveTokens();
  showLogin(message);
}

function readTokens() {
  try {
    state.access = sessionStorage.getItem(ACCESS_KEY);
    state.refresh = sessionStorage.getItem(REFRESH_KEY);
  } catch {
    // storage can be disabled (private mode, strict settings)
  }
}

function saveTokens() {
  try {
    for (const [key, value] of [[ACCESS_KEY, state.access], [REFRESH_KEY, state.refresh]]) {
      if (value) sessionStorage.setItem(key, value);
      else sessionStorage.removeItem(key);
    }
  } catch {
    // Without storage the session simply lasts until the page is reloaded.
  }
}

// ---------------------------------------------------------------- views

function showLogin(message) {
  $("chat-view").hidden = true;
  $("session").hidden = true;
  $("login-view").hidden = false;
  if (message) showLoginError(message);
  else $("login-error").hidden = true;
  $("email").focus();
}

function showLoginError(message) {
  $("login-error").textContent = message;
  $("login-error").hidden = false;
}

function showChat() {
  $("login-view").hidden = true;
  $("session").hidden = false;
  $("chat-view").hidden = false;
  $("user-name").textContent = state.user.full_name || state.user.email;
  resetConversation();
  $("question").focus();
}

function resetConversation() {
  state.history = [];
  $("messages").replaceChildren();
  $("suggestions").hidden = false;
  const firstName = (state.user.full_name || state.user.email).split(" ")[0];
  addMessage(
    "assistant",
    `Hola, ${firstName}. Puedo ayudarte con **trámites municipales** (requisitos, costos y plazos) ` +
      "y con el **estado de tus reclamos**. ¿Qué necesitas?",
  );
}

// ---------------------------------------------------------------- chat

async function send(text) {
  text = text.trim();
  if (!text || state.busy) return;

  setBusy(true);
  $("suggestions").hidden = true;
  addMessage("user", text);
  state.history.push({ role: "user", content: text });
  const typing = addTyping();

  try {
    const { reply, tool_calls } = await api("/api/chat/", { method: "POST", body: { messages: state.history } });
    state.history.push({ role: "assistant", content: reply });
    typing.remove();
    addMessage("assistant", reply, tool_calls);
  } catch (error) {
    // Drop the unanswered question so the history stays valid for the next try.
    state.history.pop();
    typing.remove();
    if (error.status === 401) return logout("Tu sesión expiró. Vuelve a ingresar.");
    addMessage("error", friendlyError(error));
    $("question").value = text;
  } finally {
    setBusy(false);
  }
}

function friendlyError(error) {
  switch (error.status) {
    case 429: return "El asistente está ocupado. Intenta de nuevo en un momento.";
    case 502:
    case 503: return "El asistente no está disponible en este momento. Intenta más tarde.";
    case 0: return error.message;
    default: return `No se pudo enviar tu consulta (${error.message}).`;
  }
}

function setBusy(busy) {
  state.busy = busy;
  $("send").disabled = busy;
  $("question").disabled = busy;
  if (!busy) $("question").focus();
}

// ---------------------------------------------------------------- rendering

function addMessage(kind, text, toolCalls = []) {
  const bubble = document.createElement("div");
  bubble.className = `message ${kind}`;

  if (kind === "assistant") renderMarkdown(bubble, text);
  else bubble.textContent = text;

  if (toolCalls.length) {
    const tools = document.createElement("div");
    tools.className = "tools";
    for (const call of toolCalls) {
      const chip = document.createElement("span");
      chip.className = call.is_error ? "tool failed" : "tool";
      chip.textContent = `${call.name}(${JSON.stringify(call.input)})`;
      chip.title = (TOOL_LABELS[call.name] || call.name) + (call.is_error ? " (sin resultado)" : "");
      tools.append(chip);
    }
    bubble.append(tools);
  }

  $("messages").append(bubble);
  bubble.scrollIntoView({ behavior: "smooth", block: "end" });
  return bubble;
}

function addTyping() {
  const bubble = document.createElement("div");
  bubble.className = "message assistant";
  bubble.setAttribute("aria-label", "El asistente está escribiendo");
  const dots = document.createElement("span");
  dots.className = "typing";
  dots.append(document.createElement("span"), document.createElement("span"), document.createElement("span"));
  bubble.append(dots);
  $("messages").append(bubble);
  bubble.scrollIntoView({ behavior: "smooth", block: "end" });
  return bubble;
}

// Claude answers in light Markdown (paragraphs, lists, **bold**). Its text is
// untrusted: it can quote complaint descriptions written by anyone. So it is
// never parsed as HTML; every piece becomes a DOM node whose text is set with
// textContent, which the browser always treats as plain text.
function renderMarkdown(container, text) {
  let list = null;
  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();
    const item = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/);
    if (item) {
      const ordered = /^\d/.test(line);
      if (!list || list.ordered !== ordered) {
        list = { element: document.createElement(ordered ? "ol" : "ul"), ordered };
        container.append(list.element);
      }
      const li = document.createElement("li");
      appendInline(li, item[1]);
      list.element.append(li);
      continue;
    }
    list = null;
    if (!line) continue;
    const paragraph = document.createElement("p");
    appendInline(paragraph, line);
    container.append(paragraph);
  }
}

function appendInline(parent, text) {
  for (const part of text.split(/(\*\*[^*]+\*\*)/g)) {
    if (!part) continue;
    if (part.length > 4 && part.startsWith("**") && part.endsWith("**")) {
      const strong = document.createElement("strong");
      strong.textContent = part.slice(2, -2);
      parent.append(strong);
    } else {
      parent.append(document.createTextNode(part));
    }
  }
}

// ---------------------------------------------------------------- wiring

function autoGrow(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
}

document.addEventListener("DOMContentLoaded", () => {
  $("login-form").addEventListener("submit", login);
  $("logout").addEventListener("click", () => logout());
  $("new-chat").addEventListener("click", resetConversation);

  $("chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const text = $("question").value;
    $("question").value = "";
    autoGrow($("question"));
    send(text);
  });

  // Enter sends; Shift+Enter adds a new line.
  $("question").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      $("chat-form").requestSubmit();
    }
  });
  $("question").addEventListener("input", (event) => autoGrow(event.target));

  for (const button of document.querySelectorAll(".suggestion")) {
    button.addEventListener("click", () => send(button.textContent));
  }

  start();
});
