# path: main.py
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 👉 seus routers estão na pasta "routers" na raiz do repo
from routers import agent, plot, profile, upload

# =========================
# App
# =========================
app = FastAPI(
    title="Backend-Desafio5-Agente-Autonomos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =========================
# CORS (ajuste se quiser restringir)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ex.: ["https://seu-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Static files (plots e uploads)
# =========================
HERE = Path(__file__).resolve().parent

PLOTS_DIR = HERE / "storage" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(PLOTS_DIR)), name="static")

UPLOADS_DIR = HERE / "storage" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
# Se quiser servir uploads também:
# app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# =========================
# Routers
# =========================
app.include_router(upload.router)   # /upload
app.include_router(profile.router)  # /profile
app.include_router(agent.router)    # /agent
app.include_router(plot.router)     # /plot

# =========================
# Healthcheck / Root
# =========================
@app.get("/health")
def health():
    return {"status": "ok", "service": "agente-backend"}

@app.get("/")
def root():
    return {
        "message": "Agente Autônomo online",
        "docs": "/docs",
        "health": "/health",
    }