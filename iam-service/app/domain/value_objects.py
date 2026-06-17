from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


# Enums de niveles 

class ClearanceLevel(str, Enum):
    BRONCE = "Bronce"
    PLATA = "Plata"
    ORO = "Oro"

    def numeric(self) -> int:
        return {"Bronce": 1, "Plata": 2, "Oro": 3}[self.value]

    def __ge__(self, other: ClearanceLevel) -> bool:
        return self.numeric() >= other.numeric()

    def __gt__(self, other: ClearanceLevel) -> bool:
        return self.numeric() > other.numeric()


class IntegrityLevel(int, Enum):
    BAJO = 1
    MEDIO = 2
    ALTO = 3


@dataclass(frozen=True)
class NivelSeguridad:
    """
    Value Object que encapsula las etiquetas de seguridad de un sujeto.
    Es inmutable: cambiar el nivel implica crear una nueva instancia.
    """
    clearance: ClearanceLevel
    integrity: IntegrityLevel

    def puede_leer(self, nivel_objeto: NivelSeguridad) -> bool:
        """Bell-LaPadula: No Read Up — clearance del sujeto >= clasificación del objeto."""
        return self.clearance >= nivel_objeto.clearance

    def puede_escribir(self, nivel_objeto: NivelSeguridad) -> bool:
        """Biba: No Write Up — integrity del sujeto >= integrity requerida del objeto."""
        return self.integrity >= nivel_objeto.integrity

    def __str__(self) -> str:
        return f"clearance={self.clearance.value}, integrity={self.integrity.value}"


@dataclass(frozen=True)
class Credenciales:
    """
    Value Object que representa las credenciales de autenticación.
    Nunca almacena la contraseña en texto plano después de la validación.
    """
    username: str
    hashed_password: str

    def __repr__(self) -> str:
        return f"Credenciales(username={self.username}, hashed_password=***)"