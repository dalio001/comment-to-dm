"""FastAPI entry point for the unified Instagram + Facebook Comment-to-DM tool."""
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
