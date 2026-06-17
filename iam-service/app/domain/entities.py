from __future__ import annotations
import uuid

from app.domain.value_objects import Credenciales, NivelSeguridad


class Usuario:
    """
    Entity: tiene identidad propia (id) que persiste aunque sus atributos cambien.
    Es el Aggregate Root del dominio IAM — todo acceso a Credenciales o
    NivelSeguridad de un usuario debe pasar por esta clase.
    """

    def __init__(
        self,
        credenciales: Credenciales,
        nivel_seguridad: NivelSeguridad,
        usuario_id: uuid.UUID | None = None,
        activo: bool = True,
    ) -> None:
        self._id = usuario_id or uuid.uuid4()
        self._credenciales = credenciales
        self._nivel_seguridad = nivel_seguridad
        self._activo = activo

    # --- Identidad ---
    @property
    def id(self) -> uuid.UUID:
        return self._id

    # --- Acceso de solo lectura a los Value Objects ---
    @property
    def credenciales(self) -> Credenciales:
        return self._credenciales

    @property
    def nivel_seguridad(self) -> NivelSeguridad:
        return self._nivel_seguridad

    @property
    def activo(self) -> bool:
        return self._activo

    # --- Comportamiento de negocio ---
    def desactivar(self) -> None:
        self._activo = False

    def cambiar_nivel_seguridad(self, nuevo_nivel: NivelSeguridad) -> None:
        """
        Cambiar nivel de seguridad reemplaza el Value Object completo
        (los VOs son inmutables, no se editan in-place).
        """
        self._nivel_seguridad = nuevo_nivel

    # --- Igualdad por identidad (regla de Entity en DDD) ---
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Usuario):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Usuario(id={self._id}, username={self._credenciales.username}, {self._nivel_seguridad})"