"use strict";

const TOKEN_KEY = "shieldops_token";

const el = (id) => document.getElementById(id);

function setMessage(text, kind) {
  const m = el("message");
  m.textContent = text || "";
  m.className = kind || "";
}

async function api(path, options) {
  const opts = options || {};
  const headers = Object.assign({}, opts.headers || {});
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch("/api" + path, {
    method: opts.method || "GET",
    headers: headers,
    body: opts.json !== undefined ? JSON.stringify(opts.json) : undefined,
  });
  let body = null;
  try {
    body = await response.json();
  } catch (e) {
    body = null;
  }
  if (!response.ok) {
    const detail = body && typeof body.detail === "string" ? body.detail : "Request failed (" + response.status + ")";
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return body;
}

function showView(signedIn, username) {
  el("auth-view").hidden = signedIn;
  el("app-view").hidden = !signedIn;
  el("session").hidden = !signedIn;
  el("whoami").textContent = signedIn ? username : "";
}

function credentials() {
  return { username: el("username").value.trim(), password: el("password").value };
}

async function login() {
  const data = await api("/auth/login", { method: "POST", json: credentials() });
  sessionStorage.setItem(TOKEN_KEY, data.access_token);
  el("password").value = "";
  await enterApp();
}

async function enterApp() {
  const me = await api("/auth/me");
  showView(true, me.username);
  setMessage("", "");
  loadDocuments();
}

function logout() {
  sessionStorage.removeItem(TOKEN_KEY);
  clearDocuments();
  showView(false);
  setMessage("Logged out.", "ok");
}

el("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("Logging in...", "");
  try {
    await login();
  } catch (error) {
    setMessage(error.message, "error");
  }
});

el("register-btn").addEventListener("click", async () => {
  if (!el("auth-form").reportValidity()) {
    return;
  }
  setMessage("Creating account...", "");
  try {
    await api("/auth/register", { method: "POST", json: credentials() });
    await login();
  } catch (error) {
    setMessage(error.message, "error");
  }
});

el("logout").addEventListener("click", logout);

if (sessionStorage.getItem(TOKEN_KEY)) {
  enterApp().catch(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    showView(false);
  });
}
