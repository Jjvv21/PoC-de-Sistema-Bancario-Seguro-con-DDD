from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class IntegrityLevel(int, Enum):
    """
    Nivel de integridad requerido por una cuenta o aportado por un proceso.
    Mismo significado que en IAM: 1=Bronce, 2=Plata, 3=Oro.
    """
    BAJO = 1
    MEDIO = 2
    ALTO = 3


class Moneda(str, Enum):
    CRC = "CRC"
    USD = "USD"
    EUR = "EUR"


@dataclass(frozen=True)
class Dinero:
    """
    Value Object inmutable que representa una cantidad monetaria con su moneda.
    Nunca se muta: cada operación retorna una nueva instancia.
    Usa Decimal (no float) para evitar errores de redondeo en dinero real.
    """
    monto: Decimal
    moneda: Moneda

    def __post_init__(self) -> None:
        if self.monto < 0:
            raise ValueError("El monto de Dinero no puede ser negativo")

    def sumar(self, otro: Dinero) -> Dinero:
        self._validar_misma_moneda(otro)
        return Dinero(monto=self.monto + otro.monto, moneda=self.moneda)

    def restar(self, otro: Dinero) -> Dinero:
        self._validar_misma_moneda(otro)
        nuevo_monto = self.monto - otro.monto
        if nuevo_monto < 0:
            raise ValueError("Fondos insuficientes: el resultado no puede ser negativo")
        return Dinero(monto=nuevo_monto, moneda=self.moneda)

    def es_mayor_o_igual(self, otro: Dinero) -> bool:
        self._validar_misma_moneda(otro)
        return self.monto >= otro.monto

    def _validar_misma_moneda(self, otro: Dinero) -> None:
        if self.moneda != otro.moneda:
            raise ValueError(f"No se puede operar {self.moneda.value} con {otro.moneda.value}")

    def __str__(self) -> str:
        return f"{self.monto} {self.moneda.value}"


@dataclass(frozen=True)
class EtiquetaSeguridad:
    """
    Value Object que representa el nivel de integridad requerido por
    una CuentaBancaria, o el que porta un proceso/usuario que intenta
    operar sobre ella. Es la pieza que el ProcesadorTransferencias usa
    para aplicar la regla Biba.
    """
    integrity: IntegrityLevel

    def puede_escribir_en(self, etiqueta_objeto: EtiquetaSeguridad) -> bool:
        """
        Biba — No Write Up: el proceso solo puede escribir si su integridad
        es igual o superior a la requerida por el objeto (la cuenta).
        """
        return self.integrity >= etiqueta_objeto.integrity
