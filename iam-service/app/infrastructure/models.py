import uuid
from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.infrastructure.database import Base


class UsuarioModel(Base):
    """
    Modelo de persistencia (ORM). Es la representación en base de datos
    del Aggregate Root Usuario. La traducción entre este modelo y la
    entidad de dominio ocurre en el Repository.
    """
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    clearance = Column(String, nullable=False)   # "Bronce" | "Plata" | "Oro"
    integrity = Column(Integer, nullable=False)   # 1 | 2 | 3
    activo = Column(Boolean, default=True)