from services.attendance_service import attendance_service
from services.camera_service import camera_service
from services.embedding_service import embedding_service
from services.faiss_service import faiss_service
from services.image_service import image_service
from services.local_storage_service import local_storage_service
from services.mediapipe_service import mediapipe_service
from services.object_storage_service import object_storage_service
from services.odoo_service import odoo_service
from services.sample_media_storage_service import sample_media_storage_service

__all__ = [
    "image_service",
    "mediapipe_service",
    "embedding_service",
    "faiss_service",
    "attendance_service",
    "odoo_service",
    "camera_service",
    "local_storage_service",
    "object_storage_service",
    "sample_media_storage_service",
]
