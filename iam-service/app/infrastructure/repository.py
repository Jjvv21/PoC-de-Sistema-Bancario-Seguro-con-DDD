import uuid
from sqlalchemy.orm import Session

from app.domain.entities import Usuario
from app.domain.value_objects import (
    Credenciales,
    NivelSeguridad,
    ClearanceLevel,
    IntegrityLevel,
)
from app.infrastructure.models import UsuarioModel


class UsuarioRepository:
    """
    Repository: encapsula el acceso a datos y traduce entre el modelo
    de persistencia (UsuarioModel) y la entidad de dominio (Usuario).
    El resto de la aplicación solo conoce Usuario, nunca UsuarioModel.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def _to_entity(self, model: UsuarioModel) -> Usuario:
        return Usuario(
            usuario_id=model.id,
            credenciales=Credenciales(
                username=model.username,
                hashed_password=model.hashed_password,
            ),
            nivel_seguridad=NivelSeguridad(
                clearance=ClearanceLevel(model.clearance),
                integrity=IntegrityLevel(model.integrity),
            ),
            activo=model.activo,
        )

    def _to_model(self, entity: Usuario) -> UsuarioModel:
        return UsuarioModel(
            id=entity.id,
            username=entity.credenciales.username,
            hashed_password=entity.credenciales.hashed_password,
            clearance=entity.nivel_seguridad.clearance.value,
            integrity=entity.nivel_seguridad.integrity.value,
            activo=entity.activo,
        )

    def obtener_por_username(self, username: str) -> Usuario | None:
        model = (
            self._db.query(UsuarioModel)
            .filter(UsuarioModel.username == username)
            .first()
        )
        return self._to_entity(model) if model else None

    def obtener_por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        model = self._db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
        return self._to_entity(model) if model else None

    def guardar(self, entity: Usuario) -> Usuario:
        model = self._to_model(entity)
        self._db.merge(model)
        self._db.commit()
        return entity

    def listar_todos(self) -> list[Usuario]:
        models = self._db.query(UsuarioModel).all()
        return [self._to_entity(m) for m in models]