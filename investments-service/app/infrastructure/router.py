from __future__ import annotations
import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.value_objects import EtiquetaConfidencialidad, NivelClearance
from app.domain.services import PermisoDenegadoError
from app.infrastructure.database import get_db
from app.infrastructure.repository import ActivoInversionRepository
from app.infrastructure.security_middleware import obtener_etiqueta_confidencialidad
from app.application.use_cases import ListarActivosUseCase

router = APIRouter(prefix="/activos", tags=["Investments"])


class ActivoResponse(BaseModel):
    id: str
    nombre: str
    valor: Decimal
    moneda: str
    clasificacion: str


class CrearActivoRequest(BaseModel):
    nombre: str
    valor: Decimal
    moneda: str


@router.get("/", response_model=list[ActivoResponse])
def listar_activos(
    db: Session = Depends(get_db),
    etiqueta_usuario: EtiquetaConfidencialidad = Depends(obtener_etiqueta_confidencialidad),
):
    """
    Escenario B de la demo: si el clearance del usuario es Bronce o Plata,
    retorna 403 Forbidden (No-Read-Up).
    """
    repository = ActivoInversionRepository(db)
    use_case = ListarActivosUseCase(repository)

    try:
        activos = use_case.ejecutar(clearance_usuario=etiqueta_usuario)
    except PermisoDenegadoError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return [
        ActivoResponse(
            id=str(a.id),
            nombre=a.nombre,
            valor=a.valor,
            moneda=a.moneda,
            clasificacion=a.clasificacion.nivel.value,
        )
        for a in activos
    ]


@router.post("/", response_model=ActivoResponse, status_code=status.HTTP_201_CREATED)
def crear_activo(payload: CrearActivoRequest, db: Session = Depends(get_db)):
    """
    Endpoint administrativo para poblar la BD durante la demo.
    Los activos siempre se crean con clasificación Oro.
    """
    from app.domain.entities import ActivoInversion
    repository = ActivoInversionRepository(db)

    activo = ActivoInversion(
        nombre=payload.nombre,
        valor=payload.valor,
        moneda=payload.moneda,
        clasificacion=EtiquetaConfidencialidad(nivel=NivelClearance.ORO),
    )
    activo = repository.crear(activo)

    return ActivoResponse(
        id=str(activo.id),
        nombre=activo.nombre,
        valor=activo.valor,
        moneda=activo.moneda,
        clasificacion=activo.clasificacion.nivel.value,
    )