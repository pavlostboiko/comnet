import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user
from app.database import get_db
from app.models import User
from app.schemas import Token, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Підбір пароля до `admin` не стримувався нічим. Лічильник у пам'яті процесу —
# бекенд працює одним контейнером, зовнішнього кешу в проєкті немає; при
# рестарті лічильник обнуляється (свідомо: це стримувач, а не блокування).
LOGIN_WINDOW_SEC = 300
LOGIN_MAX_FAILS = 10
_failed_logins: dict = defaultdict(list)


def _attempt_key(request: Request, username: str):
    client = request.client.host if request.client else "?"
    return (username or "", client)


def _recent_fails(key) -> int:
    now = time.monotonic()
    fails = [t for t in _failed_logins[key] if now - t < LOGIN_WINDOW_SEC]
    _failed_logins[key] = fails
    return len(fails)


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    key = _attempt_key(request, form.username)
    if _recent_fails(key) >= LOGIN_MAX_FAILS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Забагато невдалих спроб входу. Спробуйте за {LOGIN_WINDOW_SEC // 60} хв.",
        )
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not pwd_ctx.verify(form.password, user.hashed_password):
        _failed_logins[key].append(time.monotonic())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    _failed_logins.pop(key, None)        # успішний вхід скидає лічильник
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
