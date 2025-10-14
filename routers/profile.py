# path: agente/api/routers/profile.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException

# ✅ Router com prefixo e tag
router = APIRouter(prefix="/profile", tags=["Profile"])

# Pastas base (relativas a agente/api/)
HERE = Path(__file__).resolve().parent.parent         # .../agente/api
DATA_DIR = HERE / "storage" / "datasets"
PROFILE_DIR = HERE / "storage" / "profiles"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def _safe_name(name: str) -> str:
    """Evita path traversal: usa apenas o nome-base do arquivo."""
    return Path(name).name

def _csv_path(dataset: str) -> Path:
    """Caminho absoluto e seguro para o CSV."""
    return DATA_DIR / _safe_name(dataset)

def _profile_path(dataset: str) -> Path:
    """Caminho absoluto e seguro para o JSON de profile."""
    return PROFILE_DIR / f"{_safe_name(dataset)}_profile.json"

@router.get("/{dataset}")
def build_profile(dataset: str, chunksize: int = 100_000) -> Dict[str, Any]:
    """
    Gera um perfil estatístico básico do dataset em chunks (eficiente em memória) e salva em JSON.
    - mean/std/min/max para colunas numéricas
    - count total de linhas
    - fraud_rate quando existir coluna 'Class' binária (0/1)
    """
    csv = _csv_path(dataset)
    if not csv.exists():
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    cols: Optional[List[str]] = None
    count: int = 0
    sums: Dict[str, float] = {}
    sumsqr: Dict[str, float] = {}
    mins: Dict[str, float] = {}
    maxs: Dict[str, float] = {}

    # 1ª passada: coleta estatísticas por chunk
    try:
        for chunk in pd.read_csv(csv, chunksize=chunksize, low_memory=False):
            if cols is None:
                cols = chunk.columns.tolist()
                # inicializa dicionários
                for c in cols:
                    mins[c] = float("inf")
                    maxs[c] = float("-inf")
                    sums[c] = 0.0
                    sumsqr[c] = 0.0

            # apenas colunas numéricas deste chunk
            num_cols = [c for c in chunk.columns if pd.api.types.is_numeric_dtype(chunk[c])]
            # min/max/soma/soma^2
            for c in num_cols:
                series = pd.to_numeric(chunk[c], errors="coerce")
                # ignora NaNs
                valid = series.dropna()
                if valid.empty:
                    continue
                mn, mx = float(valid.min()), float(valid.max())
                mins[c] = mn if mn < mins[c] else mins[c]
                maxs[c] = mx if mx > maxs[c] else maxs[c]
                s = float(valid.sum())
                sums[c] += s
                sumsqr[c] += float((valid ** 2).sum())
            count += len(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar CSV: {e}")

    if cols is None:
        # CSV vazio ou sem header legível
        out = {
            "dataset": _safe_name(dataset),
            "columns": [],
            "count": 0,
            "means": {},
            "stds": {},
            "mins": {},
            "maxs": {},
            "fraud_rate": None,
        }
        _profile_path(dataset).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    # 2ª fase: calcula média e desvio padrão
    means: Dict[str, float] = {}
    stds: Dict[str, float] = {}
    denom = max(count, 1)
    for c in cols:
        if c in sums:
            mean_c = sums[c] / denom
            var_c = (sumsqr[c] / denom) - (mean_c ** 2)
            means[c] = float(mean_c)
            stds[c] = float(var_c ** 0.5) if var_c > 0 else 0.0

    # 3ª fase: taxa de fraude (se existir coluna Class)
    fraud_rate: Optional[float] = None
    if "Class" in cols:
        fraud = 0
        total = 0
        try:
            for chunk in pd.read_csv(csv, chunksize=chunksize, low_memory=False, usecols=["Class"]):
                series = pd.to_numeric(chunk["Class"], errors="coerce").fillna(0).astype(int)
                fraud += int((series == 1).sum())
                total += len(series)
            fraud_rate = (fraud / total) if total else None
        except ValueError:
            # caso 'Class' não seja lida por usecols em algum chunk, ignora
            fraud_rate = None

    out = {
        "dataset": _safe_name(dataset),
        "columns": cols,
        "count": count,
        "means": means,
        "stds": stds,
        "mins": {k: (None if v == float("inf") else v) for k, v in mins.items()},
        "maxs": {k: (None if v == float("-inf") else v) for k, v in maxs.items()},
        "fraud_rate": fraud_rate,
    }

    # persiste o profile em disco
    _profile_path(dataset).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

@router.get("/show/{dataset}")
def show_profile(dataset: str) -> Dict[str, Any]:
    """
    Retorna o JSON de profile previamente gerado por /profile/{dataset}.
    """
    p = _profile_path(dataset)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Perfil não encontrado. Gere primeiro.")
    return json.loads(p.read_text(encoding="utf-8"))