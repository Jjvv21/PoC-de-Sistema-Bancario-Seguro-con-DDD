import uuid
from sqlalchemy import Column, String, Numeric
from app.infrastructure.database import Base


class ActivoInversionModel(Base):
    __tablename__ = "activos_inversion"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    valor = Column(Numeric, nullable=False)
    moneda = Column(String, nullable=False)
    clasificacion = Column(String, nullable=False, default="Oro")