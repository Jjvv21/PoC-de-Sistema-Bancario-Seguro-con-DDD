from __future__ import annotations
import uuid
from decimal import Decimal

from app.domain.value_objects import EtiquetaConfidencialidad, NivelClearance


class ActivoInversion:
    """
    Aggregate Root del dominio de inversiones. Representa un activo
    financiero de alto valor. Su clasificación siempre es Oro — ningún
    activo de este dominio puede existir con un nivel inferior.
    """

    def __init__(
        self,
        nombre: str,
        valor: Decimal,
        moneda: str,
        clasificacion: EtiquetaConfidencialidad,
        activo_id: uuid.UUID | None = None,
    ) -> None:
        self._id = activo_id or uuid.uuid4()
        self._nombre = nombre
        self._valor = valor
        self._moneda = moneda
        self._clasificacion = clasificacion

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def valor(self) -> Decimal:
        return self._valor

    @property
    def moneda(self) -> str:
        return self._moneda

    @property
    def clasificacion(self) -> EtiquetaConfidencialidad:
        return self._clasificacion

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ActivoInversion) and self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"ActivoInversion(id={self._id}, nombre={self._nombre}, clasificacion={self._clasificacion.nivel.value})"