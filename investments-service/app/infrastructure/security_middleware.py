from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os

from app.domain.value_objects import EtiquetaConfidencialidad, NivelClearance
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
bearer_scheme = HTTPBearer()


def obtener_etiqueta_confidencialidad(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> EtiquetaConfidencialidad:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        clearance = payload.get("clearance")
        if clearance is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin clearance")
        return EtiquetaConfidencialidad(nivel=NivelClearance(clearance))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clearance inválido en token")