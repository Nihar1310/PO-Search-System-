from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import search as search_router
from .routers import chat as chat_router
from .routers import po as po_router
from .routers import system as system_router


app = FastAPI(title="PO Search & Parsing System")

# CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Create tables on startup for convenience during development
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


# Mount routers
app.include_router(search_router.router, prefix="")
app.include_router(chat_router.router, prefix="")
app.include_router(po_router.router, prefix="")
app.include_router(system_router.router, prefix="")

