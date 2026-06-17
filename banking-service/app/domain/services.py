from __future__ import annotations
import uuid
from dataclasses import dataclass

from app.domain.entities import CuentaBancaria, Transaccion, EstadoTransaccion, TipoTransaccion
from app.domain.value_objects import Dinero, EtiquetaSeguridad


@dataclass(frozen=True)
class ResultadoTransferencia:
    """
    Value Object de salida: encapsula el resultado de una transferencia
    completa (dos movimientos: salida de una cuenta, entrada en otra).
    """
    exitosa: bool
    transaccion_origen: Transaccion
    transaccion_destino: Transaccion | None
    mensaje: str


class ProcesadorTransferencias:
    """
    Domain Service: orquesta transferencias entre dos CuentaBancaria.
    No tiene identidad ni estado propio (a diferencia de un Aggregate),
    coordina el comportamiento de dos Aggregates distintos.

    La validación atómica de Biba ya vive dentro de CuentaBancaria
    (en depositar/retirar), pero este servicio es responsable de:
    1. Verificar Biba ANTES de tocar cualquier cuenta (fail-fast)
    2. Garantizar que si el retiro falla, el depósito nunca se ejecute
    3. Producir un resultado unificado de la operación completa
    """

    def transferir(
        self,
        cuenta_origen: CuentaBancaria,
        cuenta_destino: CuentaBancaria,
        monto: Dinero,
        integridad_proceso: EtiquetaSeguridad,
    ) -> ResultadoTransferencia:

        # --- Validación Biba explícita ANTES de ejecutar cualquier movimiento ---
        if not integridad_proceso.puede_escribir_en(cuenta_origen.nivel_integridad_requerido):
            transaccion_rechazada = Transaccion(
                tipo=TipoTransaccion.TRANSFERENCIA_SALIENTE,
                monto=monto,
                estado=EstadoTransaccion.RECHAZADA_BIBA,
                integridad_proceso=integridad_proceso,
                detalle=f"Violación Biba en cuenta origen: proceso integrity="
                        f"{integridad_proceso.integrity.value} < cuenta integrity="
                        f"{cuenta_origen.nivel_integridad_requerido.integrity.value}",
            )
            return ResultadoTransferencia(
                exitosa=False,
                transaccion_origen=transaccion_rechazada,
                transaccion_destino=None,
                mensaje="Transferencia rechazada: violación de integridad (Biba) en cuenta origen",
            )

        if not integridad_proceso.puede_escribir_en(cuenta_destino.nivel_integridad_requerido):
            transaccion_rechazada = Transaccion(
                tipo=TipoTransaccion.TRANSFERENCIA_ENTRANTE,
                monto=monto,
                estado=EstadoTransaccion.RECHAZADA_BIBA,
                integridad_proceso=integridad_proceso,
                detalle=f"Violación Biba en cuenta destino: proceso integrity="
                        f"{integridad_proceso.integrity.value} < cuenta integrity="
                        f"{cuenta_destino.nivel_integridad_requerido.integrity.value}",
            )
            return ResultadoTransferencia(
                exitosa=False,
                transaccion_origen=transaccion_rechazada,
                transaccion_destino=None,
                mensaje="Transferencia rechazada: violación de integridad (Biba) en cuenta destino",
            )

        # --- Ejecutar retiro primero; si falla por fondos, no se toca destino ---
        transaccion_retiro = cuenta_origen.retirar(monto, integridad_proceso)

        if transaccion_retiro.estado != EstadoTransaccion.EXITOSA:
            return ResultadoTransferencia(
                exitosa=False,
                transaccion_origen=transaccion_retiro,
                transaccion_destino=None,
                mensaje=f"Transferencia rechazada: {transaccion_retiro.detalle}",
            )

        transaccion_deposito = cuenta_destino.depositar(monto, integridad_proceso)

        return ResultadoTransferencia(
            exitosa=True,
            transaccion_origen=transaccion_retiro,
            transaccion_destino=transaccion_deposito,
            mensaje="Transferencia exitosa",
        )