# api/routers/profile.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd
import json

router = APIRouter()

DATASET_DIR = Path("api/storage/datasets")
PROFILE_DIR = Path("api/storage/profiles")
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/show/{filename}")
def show_profile(filename: str):
    """Retorna o JSON de perfil já salvo no disco (sem recalcular)."""
    p = PROFILE_DIR / f"{filename}_profile.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Perfil ainda não foi gerado.")
    with open(p, "r") as f:
        data = json.load(f)
    return data

@router.get("/{filename}")
def generate_profile(filename: str):
    csv_path = DATASET_DIR / filename
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="CSV não encontrado em api/storage/datasets.")

    # 1) Contagem total de linhas via chunks (sem carregar tudo em RAM)
    total_rows = 0
    for chunk in pd.read_csv(csv_path, chunksize=200_000, low_memory=False):
        total_rows += len(chunk)

    # 2) Sample pequeno para extrair colunas, dtypes e um describe() inicial
    sample_rows = 5000
    try:
        df_sample = pd.read_csv(csv_path, nrows=sample_rows, low_memory=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler sample do CSV: {e}")

    columns = df_sample.columns.tolist()
    dtypes = df_sample.dtypes.astype(str).to_dict()

    # describe de numéricos; se quiser incluir categóricas, use include='all'
    try:
        summary = df_sample.describe(include="all").to_dict()
    except Exception:
        summary = df_sample.describe().to_dict()

    profile = {
        "filename": filename,
        "rows_total": total_rows,
        "rows_previewed": len(df_sample),
        "columns": columns,
        "types": dtypes,
        "summary": summary
    }

    out_path = PROFILE_DIR / f"{filename}_profile.json"
    with open(out_path, "w") as f:
        json.dump(profile, f, indent=2)

    return {"message": "Profile gerado", "path": str(out_path), "rows_total": total_rows, "columns_count": len(columns)}