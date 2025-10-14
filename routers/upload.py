from fastapi import APIRouter, UploadFile, File
import shutil
from pathlib import Path

router = APIRouter()
DATASET_DIR = Path("api/storage/datasets")
DATASET_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/")
async def upload_csv(file: UploadFile = File(...)):
    path = DATASET_DIR / file.filename
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "status": "uploaded"}