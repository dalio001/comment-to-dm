const modal = document.getElementById("modal");
const form = document.getElementById("campaign-form");
const listEl = document.getElementById("campaign-list");

function openModal(campaign) {
  document.getElementById("modal-title").textContent = campaign ? "Edit campaign" : "New campaign";
  form.reset();
  document.getElementById("preview").classList.add("hidden");
  if (campaign) {
    form.id.value = campaign.id;
    form.platform.value = campaign.platform;
    form.name.value = campaign.name || "";
    form.post_id.value = campaign.post_id || "";
    form.keywords.value = campaign.keywords || "";
    form.comment_reply.value = campaign.comment_reply || "";
    form.dm_message.value = campaign.dm_message || "";
    form.active.checked = !!campaign.active;
  } else {
    form.id.value = "";
    form.active.checked = true;
  }
  modal.classList.remove("hidden");
}
function closeModal() { modal.classList.add("hidden"); }

document.getElementById("new-campaign").addEventListener("click", () => openModal(null));
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-cancel").addEventListener("click", closeModal);
modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

// Live post preview when the user leaves the Post ID field.
form.post_id.addEventListener("blur", async () => {
  const postId = form.post_id.value.trim();
  const box = document.getElementById("preview");
  if (!postId) { box.classList.add("hidden"); return; }
  try {
    const p = await api.get(`/api/post-preview?platform=${form.platform.value}&post_id=${encodeURIComponent(postId)}`);
    document.getElementById("preview-img").src = p.thumbnail || "";
    document.getElementById("preview-caption").textContent = (p.caption || "(no caption)").slice(0, 180);
    box.classList.remove("hidden");
  } catch (e) {
    box.classList.add("hidden");
    toast(`Preview failed: ${e.message}`, "err");
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    platform: form.platform.value,
    name: form.name.value,
    post_id: form.post_id.value,
    keywords: form.keywords.value,
    comment_reply: form.comment_reply.value,
    dm_message: form.dm_message.value,
    active: form.active.checked,
  };
  const id = form.id.value;
  try {
    if (id) await api.put(`/api/campaigns/${id}`, payload);
    else await api.post("/api/campaigns", payload);
    toast("Campaign saved");
    closeModal();
    loadCampaigns();
  } catch (err) {
    toast(err.message, "err");
  }
});

function esc(s) {
  return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function keywordTags(csv) {
  return (csv || "").split(",").map((k) => k.trim()).filter(Boolean)
    .map((k) => `<span>${esc(k)}</span>`).join("");
}

function card(c) {
  const el = document.createElement("div");
  el.className = "campaign";
  el.innerHTML = `
    <div class="top">
      <span class="title">${esc(c.name) || "Untitled"}</span>
      <span class="tag ${c.platform}">${c.platform}</span>
    </div>
    <div class="field"><span class="lbl">Post ID</span>${esc(c.post_id)}</div>
    <div class="field"><span class="lbl">Keywords</span><div class="kw">${keywordTags(c.keywords) || '<span class="muted">none</span>'}</div></div>
    <div class="field"><span class="lbl">Reply</span>${esc(c.comment_reply) || '<span class="muted">—</span>'}</div>
    <div class="field"><span class="lbl">DM</span>${esc(c.dm_message) || '<span class="muted">—</span>'}</div>
    <div class="actions">
      <span class="badge ${c.active ? "on" : "off"}">${c.active ? "Active" : "Inactive"}</span>
      <button class="btn-ghost" data-act="toggle">${c.active ? "Pause" : "Activate"}</button>
      <button class="btn-ghost" data-act="edit">Edit</button>
      <button class="btn-ghost" data-act="delete">Delete</button>
    </div>`;
  el.querySelector('[data-act="toggle"]').onclick = async () => {
    await api.post(`/api/campaigns/${c.id}/toggle`); loadCampaigns();
  };
  el.querySelector('[data-act="edit"]').onclick = () => openModal(c);
  el.querySelector('[data-act="delete"]').onclick = async () => {
    if (!confirm("Delete this campaign?")) return;
    await api.del(`/api/campaigns/${c.id}`); toast("Deleted"); loadCampaigns();
  };
  return el;
}

async function loadCampaigns() {
  try {
    const rows = await api.get("/api/campaigns");
    listEl.innerHTML = "";
    if (!rows.length) {
      listEl.innerHTML = '<div class="empty">No campaigns yet. Click “New campaign” to add one.</div>';
      return;
    }
    rows.forEach((c) => listEl.appendChild(card(c)));
  } catch (e) {
    toast(e.message, "err");
  }
}

loadCampaigns();
