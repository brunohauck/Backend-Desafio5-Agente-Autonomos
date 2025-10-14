# path: routers/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path

router = APIRouter(prefix="/upload", tags=["Upload"])

HERE = Path(__file__).resolve().parent.parent
UPLOAD_DIR = HERE / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """
    Faz upload de um CSV e salva em storage/uploads/.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Apenas arquivos CSV são aceitos.")

    file_path = UPLOAD_DIR / Path(file.filename).name
    try:
        contents = await file.read()
        file_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {e}")

    return JSONResponse({
        "message": "Upload realizado com sucesso",
        "file_path": str(file_path),
        "relative_path": f"/uploads/{file_path.name}"
    })