from routes.attendance import router as attendance_router
from routes.device import router as device_router
from routes.face_enrollment import router as face_enrollment_router

__all__ = ["face_enrollment_router", "attendance_router", "device_router"]
