import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.domain.value_objects import EtiquetaSeguridad, IntegrityLevel

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"

bearer_scheme = HTTPBearer()


class TokenInvalidoError(Exception):
    pass


def decodificar_token(token: str) -> dict:
    """
    Verifica la firma del JWT emitido por iam-service. Si el secret
    no coincide o el token expiró, PyJWT lanza una excepción — eso
    es justamente lo que garantiza Zero Trust: nadie puede forjar
    sus propias etiquetas de seguridad sin la clave compartida.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenInvalidoError("Token expirado")
    except jwt.InvalidTokenError:
        raise TokenInvalidoError("Token inválido")


def obtener_etiqueta_seguridad(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> EtiquetaSeguridad:
    """
    Dependency de FastAPI: se inyecta en cada endpoint que requiera
    validar Biba. Extrae el campo 'integrity' del JWT y construye el
    Value Object EtiquetaSeguridad que el dominio entiende.

    Este es el punto exacto donde Banking confía en la etiqueta emitida
    por IAM en lugar de confiar en lo que el cliente diga directamente
    — el cliente nunca puede mandar su propio nivel de integridad como
    parámetro; solo el JWT firmado por IAM es la fuente de verdad.
    """
    token = credentials.credentials
    try:
        payload = decodificar_token(token)
    except TokenInvalidoError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    integrity_raw = payload.get("integrity")
    if integrity_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene etiqueta de integridad",
        )

    try:
        integrity = IntegrityLevel(integrity_raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nivel de integridad en el token no es válido",
        )

    return EtiquetaSeguridad(integrity=integrity)


def obtener_payload_completo(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Dependency auxiliar para endpoints que necesiten más datos del
    token además de la integridad (ej. el sub/username del solicitante
    para registrar quién intentó la operación).
    """
    try:
        return decodificar_token(credentials.credentials)
    except TokenInvalidoError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))