const form = document.getElementById("config-form");

async function loadConfig() {
  try {
    const cfg = await api.get("/api/config");
    form.instagram_business_account_id.value = cfg.instagram_business_account_id || "";
    form.facebook_page_id.value = cfg.facebook_page_id || "";
    document.getElementById("ig-token-state").textContent =
      cfg.instagram_access_token_set ? `Stored: ${cfg.instagram_access_token_masked}` : "Not set";
    document.getElementById("fb-token-state").textContent =
      cfg.facebook_page_access_token_set ? `Stored: ${cfg.facebook_page_access_token_masked}` : "Not set";
  } catch (e) {
    toast(e.message, "err");
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    instagram_access_token: form.instagram_access_token.value,
    instagram_business_account_id: form.instagram_business_account_id.value,
    facebook_page_id: form.facebook_page_id.value,
    facebook_page_access_token: form.facebook_page_access_token.value,
  };
  try {
    await api.post("/api/config", payload);
    form.instagram_access_token.value = "";
    form.facebook_page_access_token.value = "";
    toast("Credentials saved");
    loadConfig();
  } catch (err) {
    toast(err.message, "err");
  }
});

loadConfig();
