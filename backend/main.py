from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.routers import auth as auth_router
from app.routers import items as items_router
from app.routers import movements as movements_router
from app.routers import settings as settings_router

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_default_admin(db: Session) -> None:
    exists = db.query(User).first()
    if not exists:
        admin = User(
            username=settings.first_admin_username,
            hashed_password=pwd_ctx.hash(settings.first_admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        create_default_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(title="ComNet API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(items_router.router)
app.include_router(movements_router.router)
app.include_router(settings_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
