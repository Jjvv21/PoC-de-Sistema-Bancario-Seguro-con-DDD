from __future__ import annotations
import uuid
from decimal import Decimal
from sqlalchemy.orm import Session

from app.domain.entities import ActivoInversion
from app.domain.value_objects import EtiquetaConfidencialidad, NivelClearance
from app.infrastructure.models import ActivoInversionModel


class ActivoInversionRepository:

    def __init__(self, db: Session) -> None:
        self._db = db

    def listar_todos(self) -> list[ActivoInversion]:
        registros = self._db.query(ActivoInversionModel).all()
        return [self._to_domain(r) for r in registros]

    def crear(self, activo: ActivoInversion) -> ActivoInversion:
        registro = ActivoInversionModel(
            id=str(activo.id),
            nombre=activo.nombre,
            valor=activo.valor,
            moneda=activo.moneda,
            clasificacion=activo.clasificacion.nivel.value,
        )
        self._db.add(registro)
        self._db.commit()
        self._db.refresh(registro)
        return self._to_domain(registro)

    def _to_domain(self, registro: ActivoInversionModel) -> ActivoInversion:
        return ActivoInversion(
            activo_id=uuid.UUID(registro.id),
            nombre=registro.nombre,
            valor=Decimal(str(registro.valor)),
            moneda=registro.moneda,
            clasificacion=EtiquetaConfidencialidad(nivel=NivelClearance(registro.clasificacion)),
        )