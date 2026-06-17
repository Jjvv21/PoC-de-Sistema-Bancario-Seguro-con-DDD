from fastapi import FastAPI

from app.infrastructure.database import Base, engine
from app.infrastructure.router import router as auth_router

app = FastAPI(
    title="SecureBankito - IAM Service",
    description="Dominio A: Gestión de Identidad y Acceso. Emite JWT con etiquetas de seguridad (Bell-LaPadula / Biba).",
    version="1.0.0",
)

app.include_router(auth_router)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "iam-service"}