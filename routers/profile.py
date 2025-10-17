# api/routers/profile.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
import json
import shutil
import pandas as pd

from api.config import STORAGE_DIR

router = APIRouter(prefix="/profile", tags=["Profile"])

class ProfileOut(BaseModel):
    message: str
    path: str
    rows_total: int
    columns_count: int

def _datasets_dir() -> Path:
    d = STORAGE_DIR / "datasets"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _uploads_dir() -> Path:
    d = STORAGE_DIR / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _profile_dir() -> Path:
    d = STORAGE_DIR / "profiles"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _resolve_dataset_path(dataset: str) -> Path:
    """
    Tenta achar o CSV primeiro em storage/datasets.
    Se não existir, tenta em storage/uploads e, se achar,
    copia para storage/datasets e retorna o caminho final em datasets.
    """
    dataset = dataset.lstrip("/")

    datasets_dir = _datasets_dir()
    uploads_dir = _uploads_dir()

    # 1) datasets/creditcard.csv
    p_datasets = datasets_dir / dataset
    if p_datasets.exists():
        return p_datasets

    # 2) Caso o front tenha mandado "uploads/creditcard.csv"
    #    ou alguém tenha passado o path completo relativo
    #    -> tentar localizar o basename em uploads/
    candidate_upload = uploads_dir / Path(dataset).name
    if candidate_upload.exists():
        # promove para datasets
        dst = datasets_dir / candidate_upload.name
        try:
            shutil.copy2(candidate_upload, dst)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Falha ao copiar de uploads para datasets: {e}")
        return dst

    # 3) Tentativa final: se dataset vier com subpasta "uploads/xyz.csv"
    if dataset.startswith("uploads/"):
        p = STORAGE_DIR / dataset
        if p.exists():
            dst = datasets_dir / p.name
            try:
                shutil.copy2(p, dst)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Falha ao copiar de uploads para datasets: {e}")
            return dst

    raise HTTPException(status_code=404, detail="Dataset não encontrado no servidor.")

@router.get("/{dataset}", response_model=ProfileOut)
def build_profile(dataset: str, chunksize: int = Query(100_000, ge=10_000, le=1_000_000)):
    """
    Gera (ou atualiza) o perfil do dataset.
    Agora também 'promove' arquivos que estejam em uploads/ para datasets/.
    """
    csv_path = _resolve_dataset_path(dataset)

    prof_path = _profile_dir() / f"{csv_path.name}_profile.json"

    # Perfil com amostragem por chunks (robusto a arquivos grandes)
    rows_total = 0
    samples = []
    for chunk in pd.read_csv(csv_path, chunksize=chunksize):
        rows_total += len(chunk)
        # amostra até 2000 linhas por chunk para descritivas
        if len(chunk) > 0:
            samples.append(chunk.sample(min(2000, len(chunk)), random_state=42))
    df_sample = pd.concat(samples, ignore_index=True) if samples else pd.DataFrame()

    out = {
        "dataset": csv_path.name,
        "rows_total": rows_total,
        "columns": list(df_sample.columns),
        "dtypes": {c: str(df_sample[c].dtype) for c in df_sample.columns},
        "desc": df_sample.describe(include="all", percentiles=[.25, .5, .75]).fillna("").to_dict(),
    }
    prof_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    return ProfileOut(
        message="Profile gerado",
        path=str(prof_path),
        rows_total=rows_total,
        columns_count=len(df_sample.columns),
    )

@router.get("/show/{dataset}")
def show_profile(dataset: str):
    """
    Mostra o JSON de perfil salvo (procura pelo nome do arquivo).
    Caso o perfil ainda não exista, retorna 404.
    """
    name = Path(dataset).name  # garante basename
    prof_path = _profile_dir() / f"{name}_profile.json"
    if not prof_path.exists():
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")
    return json.loads(prof_path.read_text())