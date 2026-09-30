from fastapi import APIRouter, HTTPException

from ..schemas import LoginRequest
from ..security import authenticate, create_access_token


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/token")
def token(payload: LoginRequest):
    user = authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_access_token(user), "token_type": "bearer", "role": user.role}
