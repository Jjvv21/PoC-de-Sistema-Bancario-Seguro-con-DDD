from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class NivelClearance(str, Enum):
    BRONCE = "Bronce"
    PLATA = "Plata"
    ORO = "Oro"

    def valor_numerico(self) -> int:
        orden = {self.BRONCE: 1, self.PLATA: 2, self.ORO: 3}
        return orden[self]


@dataclass(frozen=True)
class EtiquetaConfidencialidad:
    """
    Value Object que representa el nivel de confidencialidad de un activo
    o el clearance de un usuario. Aplica Bell-LaPadula: No Read Up.
    """
    nivel: NivelClearance

    def puede_leer(self, clasificacion_objeto: EtiquetaConfidencialidad) -> bool:
        """
        Bell-LaPadula — No Read Up: el usuario solo puede leer
        si su clearance es >= la clasificación del activo.
        """
        return self.nivel.valor_numerico() >= clasificacion_objeto.nivel.valor_numerico()