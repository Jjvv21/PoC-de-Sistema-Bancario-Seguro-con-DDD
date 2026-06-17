from fastapi import FastAPI
from app.infrastructure.database import engine, Base
from app.infrastructure.router import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Investments Service", version="1.0.0")
app.include_router(router)