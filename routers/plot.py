# path: routers/plot.py
from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use(os.getenv("MPLBACKEND", "Agg"))  # headless
import matplotlib.pyplot as plt
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/plot", tags=["Plot"])

HERE = Path(__file__).resolve().parent.parent  # raiz do projeto
DATA_DIR = HERE / "storage" / "datasets"
PLOT_DIR = HERE / "storage" / "plots"
PLOT_DIR.mkdir(parents=True, exist_ok=True)

PLOT_URL_PREFIX = "/static"  # servido em main.py com StaticFiles

def _safe_name(name: str) -> str:
    return Path(name).name

def _resp(fname: str):
    safe = _safe_name(fname)
    return {"plot_path": str(PLOT_DIR / safe), "plot_url": f"{PLOT_URL_PREFIX}/{safe}"}

@router.get("/amount_hist/{dataset}")
def amount_hist(dataset: str, bins: int = 50, log: bool = True):
    csv = DATA_DIR / _safe_name(dataset)
    if not csv.exists():
        raise HTTPException(404, "Dataset não encontrado.")
    df = pd.read_csv(csv, usecols=["Amount"])

    plt.figure(figsize=(8, 4))
    plt.hist(df["Amount"], bins=bins, log=log)
    plt.title("Distribuição de Amount")
    plt.xlabel("Amount")
    plt.ylabel("Frequência (log)" if log else "Frequência")

    fname = f"{_safe_name(dataset)}_amount_hist.png"
    plt.tight_layout(); plt.savefig(PLOT_DIR / fname); plt.close()
    return _resp(fname)

@router.get("/time_series/{dataset}")
def time_series(dataset: str, bins: int = 120):
    csv = DATA_DIR / _safe_name(dataset)
    if not csv.exists():
        raise HTTPException(404, "Dataset não encontrado.")
    df = pd.read_csv(csv, usecols=["Time"])

    cuts = pd.cut(df["Time"], bins=bins)
    series = df.groupby(cuts).size()

    plt.figure(figsize=(9, 4))
    plt.plot(range(len(series)), series.values)
    plt.title("Série temporal (contagem por intervalo)")
    plt.xlabel("Intervalo de tempo"); plt.ylabel("Contagem")

    fname = f"{_safe_name(dataset)}_time_series.png"
    plt.tight_layout(); plt.savefig(PLOT_DIR / fname); plt.close()
    return _resp(fname)

@router.get("/corr_heatmap/{dataset}")
def corr_heatmap(dataset: str, sample_rows: int = 50_000):
    csv = DATA_DIR / _safe_name(dataset)
    if not csv.exists():
        raise HTTPException(404, "Dataset não encontrado.")
    df = pd.read_csv(csv, nrows=sample_rows)

    corr = df.corr(numeric_only=True)

    plt.figure(figsize=(8, 6))
    im = plt.imshow(corr, aspect="auto")
    plt.colorbar(im)
    plt.title("Mapa de calor da correlação")
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=90, fontsize=6)
    plt.yticks(range(len(corr.columns)), corr.columns, fontsize=6)

    fname = f"{_safe_name(dataset)}_corr_heatmap.png"
    plt.tight_layout(); plt.savefig(PLOT_DIR / fname); plt.close()
    return _resp(fname)

@router.get("/box_amount_by_class/{dataset}")
def box_amount_by_class(dataset: str, max_per_class: int = 20_000):
    csv = DATA_DIR / _safe_name(dataset)
    if not csv.exists():
        raise HTTPException(404, "Dataset não encontrado.")
    df = pd.read_csv(csv, usecols=["Amount", "Class"])

    df0 = df[df["Class"] == 0]
    df1 = df[df["Class"] == 1]
    if len(df0) > 0:
        df0 = df0.sample(min(max_per_class, len(df0)), random_state=42)
    if len(df1) > 0:
        df1 = df1.sample(min(max_per_class, len(df1)), random_state=42)

    plt.figure(figsize=(6, 4))
    data = [df0["Amount"]] if len(df1) == 0 else [df0["Amount"], df1["Amount"]]
    labels = ["Normal"] if len(df1) == 0 else ["Normal", "Fraude"]
    plt.boxplot(data, labels=labels, showfliers=False)
    plt.title("Boxplot Amount por Classe")

    fname = f"{_safe_name(dataset)}_box_amount_by_class.png"
    plt.tight_layout(); plt.savefig(PLOT_DIR / fname); plt.close()
    return _resp(fname)

@router.get("/scatter_pca/{dataset}")
def scatter_pca(
    dataset: str,
    x: str = Query("V1"),
    y: str = Query("V2"),
    sample_rows: int = 50_000,
):
    csv = DATA_DIR / _safe_name(dataset)
    if not csv.exists():
        raise HTTPException(404, "Dataset não encontrado.")

    usecols = [c for c in [x, y, "Class"] if c]
    df = pd.read_csv(csv, usecols=usecols, nrows=sample_rows)

    plt.figure(figsize=(6, 5))
    if "Class" in df.columns:
        plt.scatter(df[x], df[y], c=df["Class"], s=4, alpha=0.5)
    else:
        plt.scatter(df[x], df[y], s=4, alpha=0.5)
    plt.xlabel(x); plt.ylabel(y); plt.title(f"Scatter {x} vs {y}")

    fname = f"{_safe_name(dataset)}_scatter_{x}_{y}.png"
    plt.tight_layout(); plt.savefig(PLOT_DIR / fname); plt.close()
    return _resp(fname)