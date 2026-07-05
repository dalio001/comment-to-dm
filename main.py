"""FastAPI entry point for the unified Instagram + Facebook Comment-to-DM tool."""
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from database import init_db
from routes import api, dashboard, webhook
from scheduler import start_scheduler

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Comment-to-DM Automation", version="1.0.0")

init_db()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(webhook.router)
app.include_router(api.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def _startup():
    start_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/terms", response_class=HTMLResponse)
def terms():
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Terms of Service – PLZ System</title>
<style>body{font-family:sans-serif;max-width:800px;margin:60px auto;padding:0 20px;color:#222;line-height:1.7}h1{color:#1a1a1a}h2{margin-top:2em}</style>
</head>
<body>
<h1>Terms of Service</h1>
<p><strong>Last updated:</strong> July 5, 2026</p>
<p>These Terms of Service govern your use of the PLZ System Discord bot ("the Bot"), operated by PureLivingZone LLC ("we", "us").</p>
<h2>1. Acceptance</h2>
<p>By adding or using the Bot in your Discord server, you agree to these Terms.</p>
<h2>2. Use of the Bot</h2>
<p>The Bot provides automation features for Discord servers. You agree not to use it for any unlawful purpose or in violation of Discord's Terms of Service.</p>
<h2>3. Data</h2>
<p>The Bot may collect server and user IDs necessary to provide its functionality. We do not sell or share this data with third parties.</p>
<h2>4. Termination</h2>
<p>We reserve the right to remove the Bot from any server that violates these Terms without notice.</p>
<h2>5. Disclaimer</h2>
<p>The Bot is provided "as is" without warranties of any kind. We are not liable for any damages arising from its use.</p>
<h2>6. Contact</h2>
<p>Questions? Email us at ouaja.mohamedali@gmail.com</p>
</body></html>"""


@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Privacy Policy – PLZ System</title>
<style>body{font-family:sans-serif;max-width:800px;margin:60px auto;padding:0 20px;color:#222;line-height:1.7}h1{color:#1a1a1a}h2{margin-top:2em}</style>
</head>
<body>
<h1>Privacy Policy</h1>
<p><strong>Last updated:</strong> July 5, 2026</p>
<p>This Privacy Policy explains how PureLivingZone LLC ("we", "us") collects and uses information through the PLZ System Discord bot ("the Bot").</p>
<h2>1. Information We Collect</h2>
<p>The Bot may collect Discord server IDs, channel IDs, and user IDs solely to deliver its automation functionality. No personal information beyond what Discord provides is collected.</p>
<h2>2. How We Use Information</h2>
<p>Collected data is used exclusively to operate the Bot's features within your Discord server. We do not use it for advertising or sell it to third parties.</p>
<h2>3. Data Retention</h2>
<p>Data is retained only as long as the Bot is active in your server. You may request deletion by removing the Bot.</p>
<h2>4. Third Parties</h2>
<p>We do not share your data with third parties except as required by law.</p>
<h2>5. Contact</h2>
<p>For privacy questions, contact us at ouaja.mohamedali@gmail.com</p>
</body></html>"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
