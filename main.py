from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
STORAGE_DIR = HERE / "storage"
PLOTS_DIR   = STORAGE_DIR / "plots"

from routers import upload, profile, agent, plot

asgi_app = FastAPI(title="Agente EDA (Docker/local)")

asgi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

asgi_app.include_router(upload.router,  prefix="/upload",  tags=["Upload"])
asgi_app.include_router(profile.router, prefix="/profile", tags=["Profile"])
asgi_app.include_router(agent.router,   prefix="/agent",   tags=["Agent"])
asgi_app.include_router(plot.router,    prefix="/plot",    tags=["Plot"])

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
asgi_app.mount("/static", StaticFiles(directory=str(PLOTS_DIR)), name="static")

@asgi_app.get("/health")
def health():
    return {"status": "ok"}