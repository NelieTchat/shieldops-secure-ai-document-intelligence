"use strict";

const TERMINAL_STATUSES = ["processed", "failed"];
let pollTimer = null;

function stopPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
}

function clearDocuments() {
  stopPolling();
  el("doc-list").replaceChildren();
}

function renderDocuments(docs) {
  const list = el("doc-list");
  list.replaceChildren();
  if (docs.length === 0) {
    const empty = document.createElement("li");
    empty.textContent = "No documents yet.";
    list.appendChild(empty);
    return;
  }
  docs.forEach((doc) => {
    const item = document.createElement("li");
    item.textContent = (doc.filename || doc.id) + " - " + doc.status;
    list.appendChild(item);
  });
}

async function loadDocuments() {
  stopPolling();
  let docs;
  try {
    docs = await api("/documents");
  } catch (error) {
    setMessage(error.message, "error");
    return;
  }
  if (!sessionStorage.getItem(TOKEN_KEY)) {
    return;
  }
  renderDocuments(docs);
  if (docs.some((d) => !TERMINAL_STATUSES.includes(d.status))) {
    pollTimer = setTimeout(loadDocuments, 5000);
  }
}

async function uploadFile(file) {
  const doc = await api("/documents", {
    method: "POST",
    json: { filename: file.name, size_bytes: file.size },
  });
  const form = new FormData();
  Object.entries(doc.upload.fields).forEach(([key, value]) => form.append(key, value));
  form.append("file", file);
  const response = await fetch(doc.upload.url, { method: "POST", body: form });
  if (!response.ok) {
    throw new Error("Upload to storage failed (" + response.status + ")");
  }
  await api("/documents/" + doc.id + "/complete", { method: "POST" });
}

el("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = el("file").files[0];
  if (!file) {
    return;
  }
  if (!file.name.toLowerCase().endsWith(".txt")) {
    setMessage("Only .txt files are accepted.", "error");
    return;
  }
  setMessage("Uploading...", "");
  try {
    await uploadFile(file);
    el("upload-form").reset();
    setMessage("Uploaded. Processing...", "ok");
    await loadDocuments();
  } catch (error) {
    setMessage(error.message, "error");
  }
});
