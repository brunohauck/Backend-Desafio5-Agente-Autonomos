from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers.upload import router as upload_router
from api.routers.profile import router as profile_router
from api.routers.agent import router as agent_router
from api.routers.plot import router as plot_router
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Agente EDA Autônomo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="api/storage/plots"), name="static")
app.include_router(plot_router, prefix="/plot", tags=["Plot"])
app.include_router(upload_router,  prefix="/upload",  tags=["Upload"])
app.include_router(profile_router, prefix="/profile", tags=["Profile"])
app.include_router(agent_router,   prefix="/agent",   tags=["Agent"])

@app.get("/")
def root():
    return {"message": "API do Agente EDA ativa 🚀"}