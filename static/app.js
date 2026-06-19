// Shared helpers used by settings.js and campaigns.js
window.api = {
  async get(url) { return handle(await fetch(url)); },
  async post(url, body) { return handle(await fetch(url, jsonReq("POST", body))); },
  async put(url, body) { return handle(await fetch(url, jsonReq("PUT", body))); },
  async del(url) { return handle(await fetch(url, { method: "DELETE" })); },
};

function jsonReq(method, body) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

async function handle(resp) {
  let data = null;
  try { data = await resp.json(); } catch (_) {}
  if (!resp.ok) {
    const msg = (data && (data.detail || data.message)) || `Error ${resp.status}`;
    throw new Error(msg);
  }
  return data;
}

window.toast = function (msg, kind = "ok") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className = `toast show ${kind}`;
  setTimeout(() => { el.className = "toast"; }, 3000);
};
