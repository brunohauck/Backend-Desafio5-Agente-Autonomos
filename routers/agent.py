# path: routers/agent.py
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ✅ importa do services/ na raiz do projeto
from services.llm_client import llm_respond

# Grupo de rotas /agent
router = APIRouter(prefix="/agent", tags=["Agent"])

# Pastas (relativas à raiz do projeto)
HERE = Path(__file__).resolve().parent.parent  # .../<repo-root>
DATA_DIR = HERE / "storage" / "datasets"
PROFILE_DIR = HERE / "storage" / "profiles"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# URL base do backend (para endpoints de /plot/*)
# Prioridade: BACKEND_BASE_URL > API_URL > RENDER_EXTERNAL_URL > localhost
BASE_URL = (
    os.getenv("BACKEND_BASE_URL")
    or os.getenv("API_URL")
    or os.getenv("RENDER_EXTERNAL_URL")
    or "http://localhost:10000"
)


class AgentRequest(BaseModel):
    dataset: str
    question: str


class AgentResponse(BaseModel):
    answer: str
    details: Optional[Dict[str, Any]] = None
    memory_updated: bool = True


def _json_load(p: Path) -> dict:
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _json_save(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _profile_path(dataset: str) -> Path:
    return PROFILE_DIR / f"{Path(dataset).name}_profile.json"


def _memory_path(dataset: str) -> Path:
    return PROFILE_DIR / f"{Path(dataset).name}_memory.json"


@router.post("/ask", response_model=AgentResponse)
def ask_agent(req: AgentRequest):
    """
    Responde perguntas sobre o dataset usando um LLM simples
    e (opcionalmente) aciona geração de gráficos via /plot/*.
    """
    csv = DATA_DIR / req.dataset
    if not csv.exists():
        raise HTTPException(status_code=404, detail="Dataset não encontrado no servidor.")

    profile = _json_load(_profile_path(req.dataset))
    memory = _json_load(_memory_path(req.dataset)) or {"history": [], "findings": []}

    answer, meta = llm_respond(req.question, profile, memory)

    details: Dict[str, Any] = {}
    plot_path = None
    plot_url = None

    # Requisita o gráfico ao próprio backend, se o meta sugerir
    if isinstance(meta, dict) and "plot" in meta and BASE_URL:
        plot = meta["plot"]
        try:
            if plot.get("type") == "hist_amount":
                r = requests.get(
                    f"{BASE_URL}/plot/amount_hist/{req.dataset}",
                    params={"bins": plot.get("bins", 50), "log": plot.get("log", True)},
                    timeout=180,
                )
                if r.ok:
                    j = r.json()
                    plot_path, plot_url = j.get("plot_path"), j.get("plot_url")

            elif plot.get("type") == "timeseries":
                r = requests.get(
                    f"{BASE_URL}/plot/time_series/{req.dataset}",
                    params={"bins": plot.get("bins", 120)},
                    timeout=180,
                )
                if r.ok:
                    j = r.json()
                    plot_path, plot_url = j.get("plot_path"), j.get("plot_url")

            elif plot.get("type") == "corr_heatmap":
                r = requests.get(
                    f"{BASE_URL}/plot/corr_heatmap/{req.dataset}",
                    params={"sample_rows": plot.get("sample_rows", 50_000)},
                    timeout=240,
                )
                if r.ok:
                    j = r.json()
                    plot_path, plot_url = j.get("plot_path"), j.get("plot_url")

            elif plot.get("type") == "box_amount_by_class":
                r = requests.get(
                    f"{BASE_URL}/plot/box_amount_by_class/{req.dataset}",
                    params={"max_per_class": plot.get("max_per_class", 20_000)},
                    timeout=240,
                )
                if r.ok:
                    j = r.json()
                    plot_path, plot_url = j.get("plot_path"), j.get("plot_url")

            elif plot.get("type") == "scatter":
                r = requests.get(
                    f"{BASE_URL}/plot/scatter_pca/{req.dataset}",
                    params={
                        "x": plot.get("x", "V1"),
                        "y": plot.get("y", "V2"),
                        "sample_rows": plot.get("sample_rows", 50_000),
                    },
                    timeout=240,
                )
                if r.ok:
                    j = r.json()
                    plot_path, plot_url = j.get("plot_path"), j.get("plot_url")

        except Exception as e:
            if isinstance(meta, dict):
                meta["plot_error"] = str(e)

    # Atualiza memória simples do agente
    memory["history"].append({"q": req.question, "a": answer, "plot_url": plot_url})
    _json_save(_memory_path(req.dataset), memory)

    if meta:
        details["meta"] = meta
    if plot_url:
        details["plot_url"] = plot_url
    if plot_path:
        details["plot_path"] = plot_path

    return AgentResponse(answer=answer or "Ok.", details=(details or None), memory_updated=True)