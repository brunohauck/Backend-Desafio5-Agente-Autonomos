from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter()

HERE = Path(__file__).resolve().parent.parent
DATA_DIR = HERE / "storage" / "datasets"
PROFILE_DIR = HERE / "storage" / "profiles"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def _profile_path(dataset: str) -> Path:
    return PROFILE_DIR / f"{Path(dataset).name}_profile.json"

@router.get("/{dataset}")
def build_profile(dataset: str, chunksize: int = 100_000) -> Dict[str, Any]:
    csv = DATA_DIR / dataset
    if not csv.exists():
        raise HTTPException(404, "Dataset não encontrado.")

    cols = None
    count = 0
    sums, sumsqr, mins, maxs = {}, {}, {}, {}

    for chunk in pd.read_csv(csv, chunksize=chunksize):
        if cols is None:
            cols = chunk.columns.tolist()
            for c in cols:
                mins[c] = float("inf")
                maxs[c] = float("-inf")
                sums[c] = 0.0
                sumsqr[c] = 0.0

        num_cols = [c for c in cols if c in chunk.columns and pd.api.types.is_numeric_dtype(chunk[c])]
        for c in num_cols:
            mn, mx = float(chunk[c].min()), float(chunk[c].max())
            mins[c] = min(mins[c], mn)
            maxs[c] = max(maxs[c], mx)
            s = float(chunk[c].sum())
            sums[c] += s
            sumsqr[c] += float((chunk[c] ** 2).sum())
        count += len(chunk)

    means, stds = {}, {}
    for c in cols:
        if c in sums:
            means[c] = sums[c] / max(count, 1)
            var = (sumsqr[c] / max(count, 1)) - (means[c] ** 2)
            stds[c] = (var ** 0.5) if var > 0 else 0.0

    fraud_rate = None
    if "Class" in cols:
        fraud = 0
        total = 0
        for chunk in pd.read_csv(csv, chunksize=chunksize):
            fraud += int((chunk["Class"] == 1).sum())
            total += len(chunk)
        fraud_rate = fraud / total if total else None

    out = {
        "dataset": dataset,
        "columns": cols,
        "count": count,
        "means": means,
        "stds": stds,
        "mins": mins,
        "maxs": maxs,
        "fraud_rate": fraud_rate,
    }
    _profile_path(dataset).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

@router.get("/show/{dataset}")
def show_profile(dataset: str):
    p = _profile_path(dataset)
    if not p.exists():
        raise HTTPException(404, "Perfil não encontrado. Gere primeiro.")
    return json.loads(p.read_text(encoding="utf-8"))