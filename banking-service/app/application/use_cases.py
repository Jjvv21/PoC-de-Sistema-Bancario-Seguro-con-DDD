import uuid

from app.domain.entities import CuentaBancaria, Transaccion, EstadoTransaccion
from app.domain.services import ProcesadorTransferencias, ResultadoTransferencia
from app.domain.value_objects import Dinero, EtiquetaSeguridad
from app.infrastructure.repository import CuentaBancariaRepository


class CuentaNoEncontradaError(Exception):
    pass


class CrearCuentaUseCase:
    """
    Caso de uso: crea una nueva CuentaBancaria con saldo inicial y
    su nivel de integridad requerido.
    """

    def __init__(self, repository: CuentaBancariaRepository) -> None:
        self._repository = repository

    def ejecutar(
        self,
        titular_id: uuid.UUID,
        saldo_inicial: Dinero,
        integridad_requerida: EtiquetaSeguridad,
    ) -> CuentaBancaria:
        cuenta = CuentaBancaria(
            titular_id=titular_id,
            saldo=saldo_inicial,
            nivel_integridad_requerido=integridad_requerida,
        )
        return self._repository.crear(cuenta)


class DepositarUseCase:
    """
    Caso de uso: deposita dinero en una cuenta. La validación Biba
    ocurre dentro del propio Aggregate (CuentaBancaria.depositar).
    """

    def __init__(self, repository: CuentaBancariaRepository) -> None:
        self._repository = repository

    def ejecutar(
        self,
        cuenta_id: uuid.UUID,
        monto: Dinero,
        integridad_proceso: EtiquetaSeguridad,
    ) -> Transaccion:
        cuenta = self._repository.obtener_por_id(cuenta_id)
        if cuenta is None:
            raise CuentaNoEncontradaError(f"Cuenta {cuenta_id} no existe")

        transaccion = cuenta.depositar(monto, integridad_proceso)
        self._repository.guardar(cuenta)
        return transaccion


class RetirarUseCase:
    """
    Caso de uso: retira dinero de una cuenta, validando Biba y fondos.
    """

    def __init__(self, repository: CuentaBancariaRepository) -> None:
        self._repository = repository

    def ejecutar(
        self,
        cuenta_id: uuid.UUID,
        monto: Dinero,
        integridad_proceso: EtiquetaSeguridad,
    ) -> Transaccion:
        cuenta = self._repository.obtener_por_id(cuenta_id)
        if cuenta is None:
            raise CuentaNoEncontradaError(f"Cuenta {cuenta_id} no existe")

        transaccion = cuenta.retirar(monto, integridad_proceso)
        self._repository.guardar(cuenta)
        return transaccion


class TransferirUseCase:
    """
    Caso de uso: orquesta una transferencia completa entre dos cuentas,
    usando el Domain Service ProcesadorTransferencias.
    """

    def __init__(self, repository: CuentaBancariaRepository) -> None:
        self._repository = repository
        self._procesador = ProcesadorTransferencias()

    def ejecutar(
        self,
        cuenta_origen_id: uuid.UUID,
        cuenta_destino_id: uuid.UUID,
        monto: Dinero,
        integridad_proceso: EtiquetaSeguridad,
    ) -> ResultadoTransferencia:
        cuenta_origen = self._repository.obtener_por_id(cuenta_origen_id)
        if cuenta_origen is None:
            raise CuentaNoEncontradaError(f"Cuenta origen {cuenta_origen_id} no existe")

        cuenta_destino = self._repository.obtener_por_id(cuenta_destino_id)
        if cuenta_destino is None:
            raise CuentaNoEncontradaError(f"Cuenta destino {cuenta_destino_id} no existe")

        resultado = self._procesador.transferir(
            cuenta_origen, cuenta_destino, monto, integridad_proceso
        )

        # Persistir ambas cuentas, incluso si la transferencia fue rechazada
        # (queremos el rastro de auditoría del intento fallido).
        self._repository.guardar(cuenta_origen)
        if resultado.transaccion_destino is not None:
            self._repository.guardar(cuenta_destino)

        return resultado