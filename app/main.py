from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, tasks
from app.config import settings
from app.db import init_db
from app.middleware import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Secure Tasks API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.env == "dev" else None,
    redoc_url=None,
)
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok"}