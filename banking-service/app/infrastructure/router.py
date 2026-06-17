import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.value_objects import Dinero, Moneda, EtiquetaSeguridad, IntegrityLevel
from app.domain.entities import EstadoTransaccion
from app.infrastructure.database import get_db
from app.infrastructure.repository import CuentaBancariaRepository
from app.infrastructure.security_middleware import obtener_etiqueta_seguridad
from app.application.use_cases import (
    CrearCuentaUseCase,
    DepositarUseCase,
    RetirarUseCase,
    TransferirUseCase,
    CuentaNoEncontradaError,
)

router = APIRouter(prefix="/cuentas", tags=["Banking"])


# --- Schemas (DTOs) ---

class CrearCuentaRequest(BaseModel):
    titular_id: uuid.UUID
    saldo_inicial: Decimal
    moneda: Moneda
    integridad_requerida: IntegrityLevel


class CuentaResponse(BaseModel):
    id: str
    titular_id: str
    saldo_monto: Decimal
    saldo_moneda: str
    integridad_requerida: int


class OperacionRequest(BaseModel):
    monto: Decimal
    moneda: Moneda


class TransferenciaRequest(BaseModel):
    cuenta_destino_id: uuid.UUID
    monto: Decimal
    moneda: Moneda


class TransaccionResponse(BaseModel):
    id: str
    tipo: str
    estado: str
    monto: Decimal
    moneda: str
    detalle: str


# --- Helper para mapear estado de dominio -> código HTTP ---

def _verificar_o_lanzar_403(estado: EstadoTransaccion, detalle: str) -> None:
    if estado == EstadoTransaccion.RECHAZADA_BIBA:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalle)
    if estado == EstadoTransaccion.RECHAZADA_FONDOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detalle)


# --- Endpoints ---

@router.post("/", response_model=CuentaResponse, status_code=status.HTTP_201_CREATED)
def crear_cuenta(payload: CrearCuentaRequest, db: Session = Depends(get_db)):
    repository = CuentaBancariaRepository(db)
    use_case = CrearCuentaUseCase(repository)

    cuenta = use_case.ejecutar(
        titular_id=payload.titular_id,
        saldo_inicial=Dinero(monto=payload.saldo_inicial, moneda=payload.moneda),
        integridad_requerida=EtiquetaSeguridad(integrity=payload.integridad_requerida),
    )

    return CuentaResponse(
        id=str(cuenta.id),
        titular_id=str(cuenta.titular_id),
        saldo_monto=cuenta.saldo.monto,
        saldo_moneda=cuenta.saldo.moneda.value,
        integridad_requerida=cuenta.nivel_integridad_requerido.integrity.value,
    )


@router.get("/{cuenta_id}", response_model=CuentaResponse)
def obtener_cuenta(cuenta_id: uuid.UUID, db: Session = Depends(get_db)):
    repository = CuentaBancariaRepository(db)
    cuenta = repository.obtener_por_id(cuenta_id)
    if cuenta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")

    return CuentaResponse(
        id=str(cuenta.id),
        titular_id=str(cuenta.titular_id),
        saldo_monto=cuenta.saldo.monto,
        saldo_moneda=cuenta.saldo.moneda.value,
        integridad_requerida=cuenta.nivel_integridad_requerido.integrity.value,
    )


@router.post("/{cuenta_id}/depositar", response_model=TransaccionResponse)
def depositar(
    cuenta_id: uuid.UUID,
    payload: OperacionRequest,
    db: Session = Depends(get_db),
    etiqueta_proceso: EtiquetaSeguridad = Depends(obtener_etiqueta_seguridad),
):
    """
    Escenario A de la demo: si el proceso (vía JWT) tiene integrity
    insuficiente respecto a la cuenta, esto retorna 403 Forbidden.
    """
    repository = CuentaBancariaRepository(db)
    use_case = DepositarUseCase(repository)

    try:
        transaccion = use_case.ejecutar(
            cuenta_id=cuenta_id,
            monto=Dinero(monto=payload.monto, moneda=payload.moneda),
            integridad_proceso=etiqueta_proceso,
        )
    except CuentaNoEncontradaError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    _verificar_o_lanzar_403(transaccion.estado, transaccion.detalle)

    return TransaccionResponse(
        id=str(transaccion.id),
        tipo=transaccion.tipo.value,
        estado=transaccion.estado.value,
        monto=transaccion.monto.monto,
        moneda=transaccion.monto.moneda.value,
        detalle=transaccion.detalle,
    )


@router.post("/{cuenta_id}/retirar", response_model=TransaccionResponse)
def retirar(
    cuenta_id: uuid.UUID,
    payload: OperacionRequest,
    db: Session = Depends(get_db),
    etiqueta_proceso: EtiquetaSeguridad = Depends(obtener_etiqueta_seguridad),
):
    repository = CuentaBancariaRepository(db)
    use_case = RetirarUseCase(repository)

    try:
        transaccion = use_case.ejecutar(
            cuenta_id=cuenta_id,
            monto=Dinero(monto=payload.monto, moneda=payload.moneda),
            integridad_proceso=etiqueta_proceso,
        )
    except CuentaNoEncontradaError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    _verificar_o_lanzar_403(transaccion.estado, transaccion.detalle)

    return TransaccionResponse(
        id=str(transaccion.id),
        tipo=transaccion.tipo.value,
        estado=transaccion.estado.value,
        monto=transaccion.monto.monto,
        moneda=transaccion.monto.moneda.value,
        detalle=transaccion.detalle,
    )


@router.post("/{cuenta_id}/transferir", response_model=TransaccionResponse)
def transferir(
    cuenta_id: uuid.UUID,
    payload: TransferenciaRequest,
    db: Session = Depends(get_db),
    etiqueta_proceso: EtiquetaSeguridad = Depends(obtener_etiqueta_seguridad),
):
    repository = CuentaBancariaRepository(db)
    use_case = TransferirUseCase(repository)

    try:
        resultado = use_case.ejecutar(
            cuenta_origen_id=cuenta_id,
            cuenta_destino_id=payload.cuenta_destino_id,
            monto=Dinero(monto=payload.monto, moneda=payload.moneda),
            integridad_proceso=etiqueta_proceso,
        )
    except CuentaNoEncontradaError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    _verificar_o_lanzar_403(resultado.transaccion_origen.estado, resultado.mensaje)

    transaccion = resultado.transaccion_destino or resultado.transaccion_origen
    return TransaccionResponse(
        id=str(transaccion.id),
        tipo=transaccion.tipo.value,
        estado=transaccion.estado.value,
        monto=transaccion.monto.monto,
        moneda=transaccion.monto.moneda.value,
        detalle=resultado.mensaje,
    )