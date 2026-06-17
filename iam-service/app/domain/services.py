from __future__ import annotations
from datetime import datetime, timedelta, timezone

import jwt

from app.domain.entities import Usuario


class TokenService:
    """
    Domain Service: responsable de emitir y firmar el JWT que transporta
    las etiquetas de seguridad (clearance, integrity) de un Usuario hacia
    los demás dominios (Banking, Investments).

    No pertenece a Usuario porque emitir un token requiere conocimiento
    de infraestructura criptográfica (secret, algoritmo) que no es
    responsabilidad del Aggregate Root.
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256", expiration_minutes: int = 60) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expiration_minutes = expiration_minutes

    def emitir_token(self, usuario: Usuario) -> str:
        ahora = datetime.now(timezone.utc)
        payload = {
            "sub": str(usuario.id),
            "username": usuario.credenciales.username,
            "clearance": usuario.nivel_seguridad.clearance.value,
            "integrity": usuario.nivel_seguridad.integrity.value,
            "iat": ahora,
            "exp": ahora + timedelta(minutes=self._expiration_minutes),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decodificar_token(self, token: str) -> dict:
        """
        Útil para que los otros microservicios (Banking, Investments)
        verifiquen y extraigan las etiquetas de seguridad del token.
        """
        return jwt.decode(token, self._secret_key, algorithms=[self._algorithm])