from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine, SessionLocal
from .models import User
from .security import get_password_hash
from .routers import search as search_router
from .routers import chat as chat_router
from .routers import po as po_router
from .routers import system as system_router
from .routers import auth_local as auth_local_router


app = FastAPI(title="PO Search & Parsing System")

settings = get_settings()

# CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        admin = db.query(User).filter(User.username == settings.APP_ADMIN_USERNAME).first()
        if not admin:
            password_hash = settings.APP_ADMIN_PASSWORD_HASH or (get_password_hash(settings.APP_ADMIN_PASSWORD) if settings.APP_ADMIN_PASSWORD else None)
            if not password_hash:
                raise RuntimeError('Admin user not configured. Set APP_ADMIN_PASSWORD or APP_ADMIN_PASSWORD_HASH.')
            admin = User(username=settings.APP_ADMIN_USERNAME, hashed_password=password_hash, is_active=True)
            db.add(admin)
            db.commit()


@app.get("/health")
def health():
    return {"status": "ok"}


# Mount routers
app.include_router(auth_local_router.router, prefix="")
app.include_router(search_router.router, prefix="")
app.include_router(chat_router.router, prefix="")
app.include_router(po_router.router, prefix="")
app.include_router(system_router.router, prefix="")
