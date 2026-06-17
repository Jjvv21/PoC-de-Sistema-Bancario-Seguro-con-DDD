import uuid
from decimal import Decimal
from sqlalchemy.orm import Session

from app.domain.entities import CuentaBancaria, Transaccion, TipoTransaccion, EstadoTransaccion
from app.domain.value_objects import Dinero, Moneda, EtiquetaSeguridad, IntegrityLevel
from app.infrastructure.models import CuentaBancariaModel, TransaccionModel


class CuentaBancariaRepository:
    """
    Repository del Aggregate Root CuentaBancaria. Traduce entre el
    modelo de persistencia y la entidad de dominio, incluyendo su
    historial completo de Transacciones.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def _transaccion_a_entidad(self, model: TransaccionModel) -> Transaccion:
        return Transaccion(
            transaccion_id=model.id,
            tipo=TipoTransaccion(model.tipo),
            monto=Dinero(monto=model.monto_monto, moneda=Moneda(model.monto_moneda)),
            estado=EstadoTransaccion(model.estado),
            integridad_proceso=EtiquetaSeguridad(integrity=IntegrityLevel(model.integridad_proceso)),
            timestamp=model.timestamp,
            detalle=model.detalle or "",
        )

    def _cuenta_a_entidad(self, model: CuentaBancariaModel) -> CuentaBancaria:
        cuenta = CuentaBancaria(
            cuenta_id=model.id,
            titular_id=model.titular_id,
            saldo=Dinero(monto=model.saldo_monto, moneda=Moneda(model.saldo_moneda)),
            nivel_integridad_requerido=EtiquetaSeguridad(
                integrity=IntegrityLevel(model.integridad_requerida)
            ),
        )
        # Reconstruir el historial directamente en la lista privada,
        # ya que el historial no se "agrega" sino que se restaura desde BD.
        cuenta._historial = [self._transaccion_a_entidad(t) for t in model.transacciones]
        return cuenta

    def obtener_por_id(self, cuenta_id: uuid.UUID) -> CuentaBancaria | None:
        model = self._db.query(CuentaBancariaModel).filter(CuentaBancariaModel.id == cuenta_id).first()
        return self._cuenta_a_entidad(model) if model else None

    def listar_todas(self) -> list[CuentaBancaria]:
        models = self._db.query(CuentaBancariaModel).all()
        return [self._cuenta_a_entidad(m) for m in models]

    def crear(self, cuenta: CuentaBancaria) -> CuentaBancaria:
        model = CuentaBancariaModel(
            id=cuenta.id,
            titular_id=cuenta.titular_id,
            saldo_monto=cuenta.saldo.monto,
            saldo_moneda=cuenta.saldo.moneda.value,
            integridad_requerida=cuenta.nivel_integridad_requerido.integrity.value,
        )
        self._db.add(model)
        self._db.commit()
        return cuenta

    def guardar(self, cuenta: CuentaBancaria) -> CuentaBancaria:
        """
        Persiste el saldo actualizado de la cuenta y agrega SOLO las
        transacciones nuevas (las que aún no existen en BD), para no
        duplicar el historial ya persistido.
        """
        model = self._db.query(CuentaBancariaModel).filter(CuentaBancariaModel.id == cuenta.id).first()
        if model is None:
            raise ValueError(f"Cuenta {cuenta.id} no existe en la base de datos")

        model.saldo_monto = cuenta.saldo.monto
        model.saldo_moneda = cuenta.saldo.moneda.value

        ids_existentes = {t.id for t in model.transacciones}
        for transaccion in cuenta.historial:
            if transaccion.id not in ids_existentes:
                nueva_transaccion = TransaccionModel(
                    id=transaccion.id,
                    cuenta_id=cuenta.id,
                    tipo=transaccion.tipo.value,
                    monto_monto=transaccion.monto.monto,
                    monto_moneda=transaccion.monto.moneda.value,
                    estado=transaccion.estado.value,
                    integridad_proceso=transaccion.integridad_proceso.integrity.value,
                    detalle=transaccion.detalle,
                )
                self._db.add(nueva_transaccion)

        self._db.commit()
        return cuenta