from fastapi import FastAPI

from app.infrastructure.database import Base, engine
from app.infrastructure.router import router as cuentas_router

app = FastAPI(
    title="SecureBankito - Banking Service",
    description="Dominio B: Core Bancario. Aplica el modelo Biba (No-Write-Up) sobre transacciones financieras.",
    version="1.0.0",
)

app.include_router(cuentas_router)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "banking-service"}