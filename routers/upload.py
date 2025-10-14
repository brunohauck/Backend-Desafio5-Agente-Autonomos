from __future__ import annotations
import os
from pathlib import Path
import requests
from fastapi import APIRouter, HTTPException, UploadFile, File

router = APIRouter()

HERE = Path(__file__).resolve().parent.parent
DATA_DIR = HERE / "storage" / "datasets"
DATA_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Envie um arquivo .csv")
    out = DATA_DIR / file.filename
    content = await file.read()
    out.write_bytes(content)
    return {"filename": file.filename, "size": len(content)}

@router.post("/from_url")
def upload_from_url(url: str, filename: str | None = None, max_mb: int = 300):
    """Baixa CSV direto no servidor (evita limite de upload do navegador)."""
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(400, "URL inválida.")
    fn = filename or os.path.basename(url.split("?")[0]) or "dataset.csv"
    if not fn.lower().endswith(".csv"):
        fn += ".csv"
    out = DATA_DIR / fn

    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    size, limit = 0, max_mb * 1024 * 1024
    with open(out, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > limit:
                f.close()
                out.unlink(missing_ok=True)
                raise HTTPException(413, f"Arquivo excede {max_mb}MB.")
            f.write(chunk)
    return {"filename": fn, "size": size}