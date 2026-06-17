import uuid
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base


class CuentaBancariaModel(Base):
    """
    Modelo de persistencia del Aggregate Root CuentaBancaria.
    """
    __tablename__ = "cuentas_bancarias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titular_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    saldo_monto = Column(Numeric(precision=18, scale=2), nullable=False)
    saldo_moneda = Column(String, nullable=False)
    integridad_requerida = Column(Integer, nullable=False)  # 1 | 2 | 3

    transacciones = relationship(
        "TransaccionModel", back_populates="cuenta", cascade="all, delete-orphan"
    )


class TransaccionModel(Base):
    """
    Modelo de persistencia de la Entity Transaccion — el rastro de
    auditoría. Queda enlazada a su CuentaBancaria vía FK.
    """
    __tablename__ = "transacciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id = Column(UUID(as_uuid=True), ForeignKey("cuentas_bancarias.id"), nullable=False)
    tipo = Column(String, nullable=False)
    monto_monto = Column(Numeric(precision=18, scale=2), nullable=False)
    monto_moneda = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    integridad_proceso = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    detalle = Column(String, default="")

    cuenta = relationship("CuentaBancariaModel", back_populates="transacciones")