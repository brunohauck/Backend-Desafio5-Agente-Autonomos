# path: agente/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Routers
from api.routers import agent, plot, profile, upload

# === Configuração principal ===
app = FastAPI(title="Agente Autônomo", version="1.0.0")

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Pasta estática para servir plots ===
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "storage" / "plots"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# === Inclui os routers ===
app.include_router(upload.router)
app.include_router(profile.router)
app.include_router(agent.router)
app.include_router(plot.router)

# === Healthcheck (Render usa às vezes) ===
@app.get("/health")
def health():
    return {"status": "ok", "service": "agente-api"}