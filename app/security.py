# app/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import BaseModel
from app.config.settings import get_settings

settings = get_settings()

# Esquema HTTP Bearer (Authorization: Bearer <token>)
bearer_scheme = HTTPBearer()

class TokenData(BaseModel):
    sub: int          # ID del usuario (Laravel lo envía como 'sub')
    email: str
    rol: str | None = None # Opcional, por si lo necesitas en el futuro

def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenData:
    """
    Valida el JWT emitido por Laravel usando la clave compartida (JWT_MS_SECRET).
    Verifica firma, expiración, audiencia e issuer.
    """
    
    # Excepción genérica para fallos de credenciales
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de autenticación inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Excepción específica para token expirado
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="El token ha expirado. Por favor inicie sesión nuevamente en Laravel.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    raw_token = token.credentials

    try:
        # Decodificar y validar todos los claims (aud, iss, exp, iat)
        payload = jwt.decode(
            raw_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE, # Debe ser 'fastapi-itinerarios'
            issuer=settings.JWT_ISSUER      # Debe ser 'http://localhost:8000'
        )

        # Mapeo de datos desde el payload de Laravel
        # Laravel payload structure: {'sub': 1, 'email': '...', 'rol': '...', ...}
        user_id = payload.get("sub")
        email = payload.get("email")
        rol = payload.get("rol")

        if user_id is None:
            raise credentials_exception

        return TokenData(sub=user_id, email=email, rol=rol)

    except ExpiredSignatureError:
        # python-jose lanza esto si 'exp' es menor a time.time()
        raise expired_exception
        
    except JWTError as e:
            # --- AGREGA ESTAS LINEAS PARA DEBUG ---
            print(f"\n⚠️  ERROR DE VALIDACIÓN JWT: {str(e)}")
            print(f"⚠️  Token recibido (primeros 10): {raw_token[:10]}...")
            print(f"⚠️  Clave usada: {settings.JWT_SECRET[:5]}...")
            print(f"⚠️  Audiencia esperada: {settings.JWT_AUDIENCE}")
            print(f"⚠️  Issuer esperado: {settings.JWT_ISSUER}\n")
            # --------------------------------------
            raise credentials_exception