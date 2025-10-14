# path: routers/profile.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/profile", tags=["Profile"])

HERE = Path(__file__).resolve().parent.parent
DATA_DIR = HERE / "storage" / "datasets"
PROFILE_DIR = HERE / "storage" / "profiles"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def _safe_name(name: str) -> str:
    return Path(name).name

def _csv_path(dataset: str) -> Path:
    return DATA_DIR / _safe_name(dataset)

def _profile_path(dataset: str) -> Path:
    return PROFILE_DIR / f"{_safe_name(dataset)}_profile.json"

@router.get("/{dataset}")
def build_profile(dataset: str, chunksize: int = 100_000) -> Dict[str, Any]:
    csv = _csv_path(dataset)
    if not csv.exists():
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    cols: Optional[List[str]] = None
    count: int = 0
    sums: Dict[str, float] = {}
    sumsqr: Dict[str, float] = {}
    mins: Dict[str, float] = {}
    maxs: Dict[str, float] = {}

    try:
        for chunk in pd.read_csv(csv, chunksize=chunksize, low_memory=False):
            if cols is None:
                cols = chunk.columns.tolist()
                for c in cols:
                    mins[c] = float("inf")
                    maxs[c] = float("-inf")
                    sums[c] = 0.0
                    sumsqr[c] = 0.0

            num_cols = [c for c in chunk.columns if pd.api.types.is_numeric_dtype(chunk[c])]
            for c in num_cols:
                series = pd.to_numeric(chunk[c], errors="coerce").dropna()
                if series.empty:
                    continue
                mn, mx = float(series.min()), float(series.max())
                mins[c] = mn if mn < mins[c] else mins[c]
                maxs[c] = mx if mx > maxs[c] else maxs[c]
                sums[c] += float(series.sum())
                sumsqr[c] += float((series ** 2).sum())
            count += len(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar CSV: {e}")

    if cols is None:
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

    means: Dict[str, float] = {}
    stds: Dict[str, float] = {}
    denom = max(count, 1)
    for c in cols:
        if c in sums:
            mean_c = sums[c] / denom
            var_c = (sumsqr[c] / denom) - (mean_c ** 2)
            means[c] = float(mean_c)
            stds[c] = float(var_c ** 0.5) if var_c > 0 else 0.0

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
    _profile_path(dataset).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

@router.get("/show/{dataset}")
def show_profile(dataset: str) -> Dict[str, Any]:
    p = _profile_path(dataset)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Perfil não encontrado. Gere primeiro.")
    return json.loads(p.read_text(encoding="utf-8"))