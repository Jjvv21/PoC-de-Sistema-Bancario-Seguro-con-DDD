import os
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.entities import Usuario
from app.domain.services import TokenService
from app.domain.value_objects import (
    Credenciales,
    NivelSeguridad,
    ClearanceLevel,
    IntegrityLevel,
)
from app.infrastructure.database import get_db
from app.infrastructure.repository import UsuarioRepository
from app.application.use_cases import (
    LoginUseCase,
    RegistrarUsuarioUseCase,
    CredencialesInvalidasError,
    UsuarioInactivoError,
)

router = APIRouter(prefix="/auth", tags=["IAM"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
token_service = TokenService(secret_key=SECRET_KEY)


# --- Schemas de entrada/salida (DTOs, no son el dominio) ---

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegistrarRequest(BaseModel):
    username: str
    password: str
    clearance: ClearanceLevel
    integrity: IntegrityLevel


class UsuarioResponse(BaseModel):
    id: str
    username: str
    clearance: str
    integrity: int
    activo: bool


# --- Endpoints ---

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    repository = UsuarioRepository(db)
    use_case = LoginUseCase(repository, token_service)

    try:
        token = use_case.ejecutar(payload.username, payload.password)
    except CredencialesInvalidasError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    except UsuarioInactivoError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    return LoginResponse(access_token=token)


@router.post("/registrar", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar(payload: RegistrarRequest, db: Session = Depends(get_db)):
    repository = UsuarioRepository(db)

    if repository.obtener_por_username(payload.username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El username ya existe")

    nuevo_usuario = Usuario(
        credenciales=Credenciales(username=payload.username, hashed_password=""),
        nivel_seguridad=NivelSeguridad(clearance=payload.clearance, integrity=payload.integrity),
    )

    use_case = RegistrarUsuarioUseCase(repository)
    usuario_creado = use_case.ejecutar(nuevo_usuario, payload.password)

    return UsuarioResponse(
        id=str(usuario_creado.id),
        username=usuario_creado.credenciales.username,
        clearance=usuario_creado.nivel_seguridad.clearance.value,
        integrity=usuario_creado.nivel_seguridad.integrity.value,
        activo=usuario_creado.activo,
    )


@router.get("/verificar")
def verificar_token(token: str):
    """Endpoint auxiliar para que Banking/Investments puedan probar la validación manualmente."""
    try:
        payload = token_service.decodificar_token(token)
        return {"valido": True, "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))