# api/routers/plot.py
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # backend para servidor (sem GUI)
import matplotlib.pyplot as plt

router = APIRouter()

DATASET_DIR = Path("api/storage/datasets")
PLOTS_DIR = Path("api/storage/plots")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

def _csv_path(filename: str) -> Path:
    p = DATASET_DIR / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="CSV não encontrado.")
    return p

def _save_fig(fig, image_name: str):
    out = PLOTS_DIR / image_name
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    # Devolve caminho absoluto e uma URL estática (servida pela API)
    return str(out.resolve()), f"/static/{out.name}"

@router.get("/amount_hist/{filename}")
def amount_hist(
    filename: str,
    bins: int = Query(50, ge=5, le=200),
    log: bool = True,
):
    csv_path = _csv_path(filename)

    arrays = []
    for chunk in pd.read_csv(csv_path, usecols=["Amount"], chunksize=200_000, low_memory=False):
        s = pd.to_numeric(chunk["Amount"], errors="coerce").dropna()
        if not s.empty:
            arrays.append(s.values)
    if not arrays:
        raise HTTPException(status_code=400, detail="Coluna Amount vazia ou ausente.")

    data = np.concatenate(arrays)

    fig = plt.figure()
    plt.hist(data, bins=bins, log=log)
    plt.title("Distribuição de Amount")
    plt.xlabel("Amount")
    plt.ylabel("Frequência (log)" if log else "Frequência")

    plot_path, plot_url = _save_fig(fig, f"{filename}_amount_hist.png")
    return {"plot_path": plot_path, "plot_url": plot_url}

@router.get("/time_series/{filename}")
def time_series(
    filename: str,
    bins: int = Query(120, ge=10, le=2000)
):
    csv_path = _csv_path(filename)

    arrays = []
    for chunk in pd.read_csv(csv_path, usecols=["Time"], chunksize=300_000, low_memory=False):
        s = pd.to_numeric(chunk["Time"], errors="coerce").dropna()
        if not s.empty:
            arrays.append(s.values.astype(float))
    if not arrays:
        raise HTTPException(status_code=400, detail="Coluna Time vazia ou ausente.")

    t = np.concatenate(arrays)
    counts, edges = np.histogram(t, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2

    fig = plt.figure()
    plt.plot(centers, counts)
    plt.title("Contagem de Transações ao Longo do Tempo")
    plt.xlabel("Time (s desde a 1ª transação)")
    plt.ylabel("Contagem por janela")

    plot_path, plot_url = _save_fig(fig, f"{filename}_time_series_{bins}.png")
    return {"plot_path": plot_path, "plot_url": plot_url}