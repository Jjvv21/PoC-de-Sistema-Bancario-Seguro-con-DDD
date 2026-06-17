import bcrypt

from app.domain.entities import Usuario
from app.domain.services import TokenService
from app.infrastructure.repository import UsuarioRepository

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

class CredencialesInvalidasError(Exception):
    """Se lanza cuando username/password no coinciden o el usuario no existe."""
    pass


class UsuarioInactivoError(Exception):
    """Se lanza cuando el usuario existe pero está desactivado."""
    pass


class LoginUseCase:
    """
    Caso de uso: autentica a un usuario y, si es exitoso, emite un JWT
    con sus etiquetas de seguridad (clearance, integrity) para que los
    demás dominios (Banking, Investments) puedan validar Biba y Bell-LaPadula.
    """

    def __init__(self, repository: UsuarioRepository, token_service: TokenService) -> None:
        self._repository = repository
        self._token_service = token_service

    def ejecutar(self, username: str, password: str) -> str:
        usuario = self._repository.obtener_por_username(username)

        if usuario is None:
            raise CredencialesInvalidasError("Usuario o contraseña incorrectos")

        if not usuario.activo:
            raise UsuarioInactivoError("El usuario está desactivado")

        if not _verify_password(password, usuario.credenciales.hashed_password):
            raise CredencialesInvalidasError("Usuario o contraseña incorrectos")

        return self._token_service.emitir_token(usuario)


class RegistrarUsuarioUseCase:
    """
    Caso de uso: registra un nuevo usuario con sus niveles de seguridad
    iniciales. En un sistema real esto estaría restringido a administradores.
    """

    def __init__(self, repository: UsuarioRepository) -> None:
        self._repository = repository

    def ejecutar(self, usuario: Usuario, password_plano: str) -> Usuario:
        from app.domain.value_objects import Credenciales

        hashed = _hash_password(password_plano)
        usuario_con_hash = Usuario(
            usuario_id=usuario.id,
            credenciales=Credenciales(
                username=usuario.credenciales.username,
                hashed_password=hashed,
            ),
            nivel_seguridad=usuario.nivel_seguridad,
            activo=usuario.activo,
        )
        return self._repository.guardar(usuario_con_hash)
