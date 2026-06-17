from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum

from app.domain.value_objects import Dinero, EtiquetaSeguridad


class TipoTransaccion(str, Enum):
    DEPOSITO = "DEPOSITO"
    RETIRO = "RETIRO"
    TRANSFERENCIA_ENTRANTE = "TRANSFERENCIA_ENTRANTE"
    TRANSFERENCIA_SALIENTE = "TRANSFERENCIA_SALIENTE"


class EstadoTransaccion(str, Enum):
    EXITOSA = "EXITOSA"
    RECHAZADA_BIBA = "RECHAZADA_BIBA"  # rechazada por violar No-Write-Up
    RECHAZADA_FONDOS = "RECHAZADA_FONDOS"


class Transaccion:
    """
    Entity: representa un movimiento sobre una cuenta. Tiene identidad
    propia (id único) y es inmutable una vez creada — un Aggregate no
    modifica una Transaccion existente, solo agrega nuevas.
    Funciona como rastro de auditoría: queda registro incluso de los
    intentos rechazados por Biba.
    """

    def __init__(
        self,
        tipo: TipoTransaccion,
        monto: Dinero,
        estado: EstadoTransaccion,
        integridad_proceso: EtiquetaSeguridad,
        transaccion_id: uuid.UUID | None = None,
        timestamp: datetime | None = None,
        detalle: str = "",
    ) -> None:
        self._id = transaccion_id or uuid.uuid4()
        self._tipo = tipo
        self._monto = monto
        self._estado = estado
        self._integridad_proceso = integridad_proceso
        self._timestamp = timestamp or datetime.now(timezone.utc)
        self._detalle = detalle

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def tipo(self) -> TipoTransaccion:
        return self._tipo

    @property
    def monto(self) -> Dinero:
        return self._monto

    @property
    def estado(self) -> EstadoTransaccion:
        return self._estado

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def detalle(self) -> str:
        return self._detalle
    
    @property
    def integridad_proceso(self):
        return self._integridad_proceso

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Transaccion) and self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Transaccion(id={self._id}, tipo={self._tipo.value}, estado={self._estado.value}, monto={self._monto})"


class CuentaBancaria:
    """
    Aggregate Root del dominio bancario. Toda operación sobre el saldo
    o el historial de transacciones DEBE pasar por esta clase — nunca
    se accede ni modifica una Transaccion directamente desde fuera.

    Encapsula su propia EtiquetaSeguridad (integridad requerida): nadie
    puede escribir en ella sin que su integridad sea >= la de la cuenta.
    """

    def __init__(
        self,
        titular_id: uuid.UUID,
        saldo: Dinero,
        nivel_integridad_requerido: EtiquetaSeguridad,
        cuenta_id: uuid.UUID | None = None,
    ) -> None:
        self._id = cuenta_id or uuid.uuid4()
        self._titular_id = titular_id
        self._saldo = saldo
        self._nivel_integridad_requerido = nivel_integridad_requerido
        self._historial: list[Transaccion] = []

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def titular_id(self) -> uuid.UUID:
        return self._titular_id

    @property
    def saldo(self) -> Dinero:
        return self._saldo

    @property
    def nivel_integridad_requerido(self) -> EtiquetaSeguridad:
        return self._nivel_integridad_requerido

    @property
    def historial(self) -> list[Transaccion]:
        return list(self._historial)

    def depositar(self, monto: Dinero, integridad_proceso: EtiquetaSeguridad) -> Transaccion:
        if not integridad_proceso.puede_escribir_en(self._nivel_integridad_requerido):
            transaccion_rechazada = Transaccion(
                tipo=TipoTransaccion.DEPOSITO,
                monto=monto,
                estado=EstadoTransaccion.RECHAZADA_BIBA,
                integridad_proceso=integridad_proceso,
                detalle=f"Violación Biba: proceso integrity={integridad_proceso.integrity.value} "
                        f"< cuenta integrity={self._nivel_integridad_requerido.integrity.value}",
            )
            self._historial.append(transaccion_rechazada)
            return transaccion_rechazada

        self._saldo = self._saldo.sumar(monto)
        transaccion = Transaccion(
            tipo=TipoTransaccion.DEPOSITO,
            monto=monto,
            estado=EstadoTransaccion.EXITOSA,
            integridad_proceso=integridad_proceso,
            detalle="Depósito exitoso",
        )
        self._historial.append(transaccion)
        return transaccion

    def retirar(self, monto: Dinero, integridad_proceso: EtiquetaSeguridad) -> Transaccion:
        if not integridad_proceso.puede_escribir_en(self._nivel_integridad_requerido):
            transaccion_rechazada = Transaccion(
                tipo=TipoTransaccion.RETIRO,
                monto=monto,
                estado=EstadoTransaccion.RECHAZADA_BIBA,
                integridad_proceso=integridad_proceso,
                detalle=f"Violación Biba: proceso integrity={integridad_proceso.integrity.value} "
                        f"< cuenta integrity={self._nivel_integridad_requerido.integrity.value}",
            )
            self._historial.append(transaccion_rechazada)
            return transaccion_rechazada

        if not self._saldo.es_mayor_o_igual(monto):
            transaccion_rechazada = Transaccion(
                tipo=TipoTransaccion.RETIRO,
                monto=monto,
                estado=EstadoTransaccion.RECHAZADA_FONDOS,
                integridad_proceso=integridad_proceso,
                detalle="Fondos insuficientes",
            )
            self._historial.append(transaccion_rechazada)
            return transaccion_rechazada

        self._saldo = self._saldo.restar(monto)
        transaccion = Transaccion(
            tipo=TipoTransaccion.RETIRO,
            monto=monto,
            estado=EstadoTransaccion.EXITOSA,
            integridad_proceso=integridad_proceso,
            detalle="Retiro exitoso",
        )
        self._historial.append(transaccion)
        return transaccion

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CuentaBancaria) and self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"CuentaBancaria(id={self._id}, saldo={self._saldo}, integridad_requerida={self._nivel_integridad_requerido.integrity.value})"