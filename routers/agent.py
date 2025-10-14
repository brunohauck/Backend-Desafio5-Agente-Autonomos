# api/routers/agent.py
from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# importa seu cliente LLM (mantém como estava no seu projeto)
# llm_respond(question: str, profile: dict, memory: dict) -> tuple[str, dict|None]
from api.services.llm_client import llm_respond

router = APIRouter()

# Diretórios de armazenamento
BASE_DIR = Path("api/storage")
DATASET_DIR = BASE_DIR / "datasets"
PROFILE_DIR = BASE_DIR / "profiles"
MEMORY_DIR = BASE_DIR / "profiles"   # pode ser o mesmo dir; ajuste se usar outro

# URL base do próprio backend (para chamar endpoints /plot)
# Defina no painel do cPanel (Environment Variables): BACKEND_BASE_URL=http://python.startdev.net
BASE_URL = os.getenv("BACKEND_BASE_URL", "http://python.startdev.net")

# -----------------------------
# Models
# -----------------------------
class AgentRequest(BaseModel):
    dataset: str
    question: str

class AgentResponse(BaseModel):
    answer: str
    details: Optional[Dict[str, Any]] = None
    memory_updated: bool = True

# -----------------------------
# Helpers
# -----------------------------
def _json_load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _json_save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _profile_path(dataset: str) -> Path:
    # nome do perfil pode ser <dataset>_profile.json; ajuste se usa outro padrão
    name = f"{Path(dataset).name}_profile.json"
    return PROFILE_DIR / name

def _memory_path(dataset: str) -> Path:
    name = f"{Path(dataset).name}_memory.json"
    return PROFILE_DIR / name

# -----------------------------
# Endpoint principal
# -----------------------------
@router.post("/ask", response_model=AgentResponse)
def ask_agent(req: AgentRequest):
    # verifica dataset existe
    csv_path = DATASET_DIR / req.dataset
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Dataset não encontrado no servidor.")

    # carrega perfil + memória
    profile = _json_load(_profile_path(req.dataset))
    memory = _json_load(_memory_path(req.dataset)) or {"history": [], "findings": []}

    # chama LLM para gerar resposta e possivelmente meta de gráficos
    answer, meta = llm_respond(req.question, profile, memory)

    details: Dict[str, Any] = {}
    plot_path = None
    plot_url = None
    plot_paths = None

    # Caso o LLM traga instrução de plot em meta.plot
    if isinstance(meta, dict) and "plot" in meta:
        plot = meta["plot"]
        try:
            if plot.get("type") == "hist_amount":
                r = requests.get(
                    f"{BASE_URL}/plot/amount_hist/{req.dataset}",
                    params={
                        "bins": plot.get("bins", 50),
                        "log": plot.get("log", True),
                    },
                    timeout=120,
                )
                if r.ok:
                    j = r.json()
                    plot_path = j.get("plot_path")
                    plot_url = j.get("plot_url")

            elif plot.get("type") == "timeseries":
                r = requests.get(
                    f"{BASE_URL}/plot/time_series/{req.dataset}",
                    params={"bins": plot.get("bins", 120)},
                    timeout=120,
                )
                if r.ok:
                    j = r.json()
                    plot_path = j.get("plot_path")
                    plot_url = j.get("plot_url")

            elif plot.get("type") == "corr_heatmap":
                r = requests.get(
                    f"{BASE_URL}/plot/corr_heatmap/{req.dataset}",
                    params={"sample_rows": plot.get("sample_rows", 50000)},
                    timeout=180,
                )
                if r.ok:
                    j = r.json()
                    plot_path = j.get("plot_path")
                    plot_url = j.get("plot_url")

            elif plot.get("type") == "box_amount_by_class":
                r = requests.get(
                    f"{BASE_URL}/plot/box_amount_by_class/{req.dataset}",
                    params={"max_per_class": plot.get("max_per_class", 20000)},
                    timeout=180,
                )
                if r.ok:
                    j = r.json()
                    plot_path = j.get("plot_path")
                    plot_url = j.get("plot_url")

            elif plot.get("type") == "scatter":
                # 👉 ESTE É O TRECHO QUE VOCÊ MENCIONOU (reposto e atualizado para BASE_URL)
                r = requests.get(
                    f"{BASE_URL}/plot/scatter_pca/{req.dataset}",
                    params={
                        "x": plot.get("x", "V1"),
                        "y": plot.get("y", "V2"),
                        "sample_rows": plot.get("sample_rows", 50000),
                    },
                    timeout=180,
                )
                if r.ok:
                    j = r.json()
                    plot_path = j.get("plot_path")
                    plot_url = j.get("plot_url")

        except Exception as e:
            # não derruba a resposta; apenas anexa erro de plot
            meta = meta or {}
            meta["plot_error"] = str(e)

    # Atualiza memória (histórico e conclusões)
    memory["history"].append(
        {
            "q": req.question,
            "a": answer,
            "plot_path": plot_path,
            "plot_url": plot_url,
        }
    )
    if any(k in (answer or "").lower() for k in ("conclus", "insight", "recomend")):
        memory["findings"].append({"text": (answer or "")[:400], "source": "llm"})

    _json_save(_memory_path(req.dataset), memory)

    # monta details
    if meta:
        details["meta"] = meta
    if plot_path:
        details["plot_path"] = plot_path
    if plot_url:
        details["plot_url"] = plot_url
    if plot_paths:
        details["plot_paths"] = plot_paths

    return AgentResponse(
        answer=answer or "Ok.",
        details=(details or None),
        memory_updated=True,
    )