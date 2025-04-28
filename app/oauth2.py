# app/oauth2.py
import logging
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from . import schemas, database, models
from .config import settings
from typing import Optional
from jose.exceptions import ExpiredSignatureError
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class OAuth2PasswordBearerOptional(OAuth2PasswordBearer):
    """
    OAuth2 password bearer that doesn't force authentication.
    Returns None instead of raising an exception if no token is provided.
    """

    async def __call__(self, request: Request) -> Optional[str]:
        try:
            return await super().__call__(request)
        except HTTPException:
            return None


# Define oauth2_scheme once, with auto_error=False for optional authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
oauth2_scheme_optional = OAuth2PasswordBearerOptional(tokenUrl="auth/login")

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

EXTERNAL_API_KEY = os.getenv("EXTERNAL_API_KEY")
if not EXTERNAL_API_KEY:
    raise ValueError("EXTERNAL_API_KEY not set in environment variables")

# Define API key scheme for header authentication
api_key_header = APIKeyHeader(name="X-API-Key")


# Dependency for API key authentication
async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != EXTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return api_key


def create_access_token(data: dict):
    print(f"DEBUG: Creating access token with data: {data}")
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("sub")  # Change to "sub" to match the payload
        if id is None:
            raise credentials_exception
        token_data = schemas.TokenData(id=id)

        # Add a debug check
        if not hasattr(token_data, "id") or token_data.id is None:
            raise ValueError("TokenData missing id attribute")

        return token_data
    except JWTError:
        raise credentials_exception
    except Exception as e:
        print(f"DEBUG: Token verification error: {str(e)}")
        raise credentials_exception


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        # Decode the token to get user data
        token_data = verify_access_token(token, credentials_exception)

        # Use token_data.id instead of token_data.sub
        user = db.query(models.User).filter(models.User.id == token_data.id).first()

        if user is None:
            raise credentials_exception

        return user
    except SQLAlchemyError as db_error:
        raise HTTPException(status_code=500, detail="A database error occurred.")
    except JWTError:
        raise credentials_exception


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
):
    if not token:
        return None  # No token provided, return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Use the local verify_access_token function
        token_data = verify_access_token(token, credentials_exception)
        user_id = token_data.id  # Use token_data.id instead of payload.get("sub")

        if not user_id:
            return None

        user = db.query(models.User).filter(models.User.id == user_id).first()
        return user

    except JWTError:
        return None  # Invalid token, return None


async def verify_api_key(api_key: str = Depends(api_key_header)):
    """
    Verifies the API key and returns True if valid.
    This is a convenience wrapper around get_api_key for endpoints
    that only need to check if the key is valid.
    """
    # This will raise an HTTPException if the key is invalid
    await get_api_key(api_key)
    return True


# Use the already-defined oauth2_scheme_optional
async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(database.get_db),
) -> Optional[models.User]:
    """
    Get the current user if a valid token is provided, otherwise return None.
    This allows endpoints to support both authenticated and unauthenticated access.
    """
    if not token:
        return None

    try:
        # Your existing token validation logic
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        id: str = payload.get("sub")

        if id is None:
            return None

        user = db.query(models.User).filter(models.User.id == id).first()
        if not user:
            return None

        return user
    except JWTError:
        return None
