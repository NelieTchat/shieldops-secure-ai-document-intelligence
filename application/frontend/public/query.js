"use strict";

function documentNameForKey(key, docs) {
  const last = key.split("/").pop() || key;
  const docId = last.replace(/[.]txt$/, "");
  const match = docs.find((d) => d.id === docId);
  return match && match.filename ? match.filename : last;
}

function renderCitations(citations, docs) {
  const list = el("citations");
  list.replaceChildren();
  citations.forEach((c) => {
    const item = document.createElement("li");
    item.textContent = documentNameForKey(c.key, docs) + " (section " + (c.chunk_index + 1) + ")";
    list.appendChild(item);
  });
}

el("query-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = el("question").value.trim();
  if (!question) {
    return;
  }
  const button = el("ask-btn");
  button.disabled = true;
  el("answer").textContent = "";
  el("citations").replaceChildren();
  setMessage("Thinking...", "");
  try {
    const result = await api("/query", { method: "POST", json: { question: question } });
    const docs = await api("/documents");
    el("answer").textContent = result.answer;
    renderCitations(result.citations || [], docs);
    setMessage("", "");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    button.disabled = false;
  }
});
