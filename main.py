import asyncio
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config.database import SessionLocal, check_database_connection
from config.settings import settings
from models.face_attendance import FaceTemplate
from routes import attendance_router, auth_router, device_router, face_enrollment_router, hr_router
from services.faiss_service import faiss_service
from services.system_health_service import system_health_service
from services.attendance_service import attendance_service
from services.metrics_service import metrics_service
from supports.security import require_api_key
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
    faiss_service.persist()
    print(f"FAISS index loaded with {len(templates)} templates.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with SessionLocal() as db:
            _load_faiss_index_on_startup(db)
    except SQLAlchemyError as exc:
        # Keep health and API routes available while the database is starting
        # or temporarily unavailable. Requests using the DB will still return
        # their normal database error until connectivity is restored.
        print(f"Face index startup skipped: {exc}")
    retry_task = None
    if settings.odoo_retry_worker_enabled and settings.odoo_integration_enabled:
        retry_task = asyncio.create_task(_odoo_retry_loop())
    try:
        yield
    finally:
        if retry_task:
            retry_task.cancel()
            await asyncio.gather(retry_task, return_exceptions=True)


async def _odoo_retry_loop():
    """Periodically replay failed Odoo syncs in a worker thread."""
    while True:
        try:
            await asyncio.to_thread(_retry_failed_syncs_once)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Odoo retry worker failed: {exc}")
        await asyncio.sleep(max(10, settings.odoo_retry_interval_seconds))


def _retry_failed_syncs_once() -> None:
    with SessionLocal() as db:
        result = attendance_service.retry_failed_syncs(db, limit=settings.odoo_retry_batch_size)
        if result["total"]:
            print(
                f"Odoo retry worker processed {result['total']} syncs; "
                f"succeeded={result['succeeded']}"
            )


app = FastAPI(title=settings.app_name, lifespan=lifespan)
register_exception_handlers(app)

cors_origins = [
    origin.strip()
    for origin in settings.backend_cors_origins.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def collect_request_metrics(request: Request, call_next):
    started_at = perf_counter()
    response = await call_next(request)
    metrics_service.observe_request(request.url.path, response.status_code, started_at)
    return response


app.include_router(auth_router)
app.include_router(face_enrollment_router)
app.include_router(attendance_router)
app.include_router(device_router)
app.include_router(hr_router)

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
    inference = system_health_service.inference_health()
    return JSONResponse(
        status_code=200,
        content={
            "service": "fastapi-fd",
            "healthy": inference["ready"],
            "inference": inference,
        },
    )


@app.get("/metrics", dependencies=[Depends(require_api_key)])
def metrics() -> JSONResponse:
    return JSONResponse(status_code=200, content=metrics_service.snapshot())


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
