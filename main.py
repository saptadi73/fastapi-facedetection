from datetime import datetime, timezone
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.database import SessionLocal, check_database_connection
from config.settings import settings
from models.face_attendance import FaceTemplate
from routes import attendance_router, device_router, face_enrollment_router
from services.faiss_service import faiss_service
from supports.exception_handlers import register_exception_handlers


def _load_faiss_index_on_startup(db: Session):
    """Loads active face templates into the FAISS index."""
    if not faiss_service.is_empty():
        return
    templates = db.scalars(select(FaceTemplate).where(FaceTemplate.is_active.is_(True))).all()
    for template in templates:
        faiss_service.add_embedding(
            employee_map_id=template.employee_map_id,
            embedding=template.embedding_vector,
            template_id=template.id,
        )
    print(f"FAISS index loaded with {len(templates)} templates.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        _load_faiss_index_on_startup(db)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
register_exception_handlers(app)
app.include_router(face_enrollment_router)
app.include_router(attendance_router)
app.include_router(device_router)

uploads_root = Path(settings.base_dir) / "uploads"
uploads_root.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_root)), name="uploads")


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "message": "FastAPI is running",
            "docs": "/docs",
        },
    )


@app.get("/test")
def test_response() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "message": "Auto response for local test",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/health")
def health_check() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "service": "fastapi-fd",
            "healthy": True,
        },
    )


@app.get("/db-check")
def db_check() -> JSONResponse:
    ok, detail = check_database_connection()
    status_code = 200 if ok else 500
    return JSONResponse(
        status_code=status_code,
        content={
            "database": "postgresql",
            "connected": ok,
            "detail": detail,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
