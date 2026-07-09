from __future__ import annotations

import base64
import io

from models.face_attendance import FaceEmployeeMap, FaceTemplate
from services.faiss_service import faiss_service


def _build_image() -> "Image.Image":
    from PIL import Image

    width, height = 128, 128
    image = Image.new("RGB", (width, height))
    image.putdata(
        [
            ((x * 13 + y * 17) % 256, (x * 3 + y * 11) % 256, (x * 7 + y * 19) % 256)
            for y in range(height)
            for x in range(width)
        ]
    )
    return image


def _build_image_base64(image_format: str = "PNG", quality: int = 95) -> str:
    image = _build_image()
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, quality=quality)
    return base64.b64encode(buffer.getvalue()).decode()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "fastapi-fd"
    assert payload["healthy"] is True
    assert "inference" in payload
    assert "cpu" in payload["inference"]
    assert "avx_available" in payload["inference"]["cpu"]
    assert "avx2_available" in payload["inference"]["cpu"]
    assert "onnxruntime" in payload["inference"]
    assert "model" in payload["inference"]


def test_error_envelope_for_unknown_employee(client):
    image_base64 = _build_image_base64()
    response = client.post(
        "/api/v1/face/enroll/sample",
        json={"employee_id": "UNKNOWN", "image_base64": image_base64},
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["code"] == "EMPLOYEE_NOT_FOUND"
    assert "timestamp_utc" in payload


def test_enrollment_and_checkin_flow(client, db_session):
    image_base64 = _build_image_base64()

    response = client.post(
        "/api/v1/device",
        json={
            "device_code": "CAM-T1",
            "device_name": "Test Camera",
            "location": "Lab",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/api/v1/face/enroll/start",
        json={
            "employee_id": "EMP-T1",
            "employee_name": "Test Employee",
            "employee_code": "E-T1",
        },
    )
    assert response.status_code == 201

    for _ in range(5):
        response = client.post(
            "/api/v1/face/enroll/sample",
            json={"employee_id": "EMP-T1", "image_base64": image_base64},
        )
        assert response.status_code == 201
        sample_payload = response.json()["data"]
        assert sample_payload["accepted"] is True
        assert "storage" in sample_payload
        assert sample_payload["storage"]["local_path"]
        assert sample_payload["storage"]["local_url"].startswith("/uploads/")
        assert sample_payload["storage"]["object_url"].startswith("http://")
        assert sample_payload["storage"]["odoo_attachment_id"]

    response = client.post(
        "/api/v1/face/enroll/finish",
        json={"employee_id": "EMP-T1", "notes": "done"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "completed"
    assert response.json()["data"]["templates_created"] == 5
    assert response.json()["data"]["embedding_provider"] in {"visual", "onnx"}

    employee = db_session.query(FaceEmployeeMap).filter_by(employee_id="EMP-T1").one()
    active_templates = db_session.query(FaceTemplate).filter_by(employee_map_id=employee.id, is_active=True).count()
    assert active_templates == 5

    response = client.post(
        "/api/v1/attendance/checkin",
        json={
            "device_code": "CAM-T1",
            "image_base64": image_base64,
            "latitude": -6.2000001,
            "longitude": 106.8166662,
            "gps_accuracy_meters": 12.5,
            "gps_provider": "browser",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["matched"] is True
    assert payload["data"]["employee_id"] == "EMP-T1"
    assert payload["data"]["embedding_provider"] in {"visual", "onnx"}
    assert payload["data"]["odoo_sync_status"] == "success"
    assert payload["data"]["odoo_attendance_id"]
    assert payload["data"]["status"] == "success"
    assert payload["data"]["latitude"] == -6.2000001
    assert payload["data"]["longitude"] == 106.8166662
    assert payload["data"]["gps_accuracy_meters"] == 12.5


def test_reencoded_attendance_image_still_matches(client):
    enrolled_image_base64 = _build_image_base64("PNG")
    attendance_image_base64 = _build_image_base64("JPEG", quality=90)

    response = client.post(
        "/api/v1/face/enroll/start",
        json={
            "employee_id": "EMP-JPEG",
            "employee_name": "JPEG Employee",
            "employee_code": "E-JPEG",
        },
    )
    assert response.status_code == 201

    for _ in range(5):
        response = client.post(
            "/api/v1/face/enroll/sample",
            json={"employee_id": "EMP-JPEG", "image_base64": enrolled_image_base64},
        )
        assert response.status_code == 201
        assert response.json()["data"]["accepted"] is True

    response = client.post(
        "/api/v1/face/enroll/finish",
        json={"employee_id": "EMP-JPEG"},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/attendance/checkin",
        json={"image_base64": attendance_image_base64},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["matched"] is True
    assert payload["employee_id"] == "EMP-JPEG"


def test_attendance_reloads_empty_face_index_from_templates(client):
    image_base64 = _build_image_base64()

    response = client.post(
        "/api/v1/face/enroll/start",
        json={
            "employee_id": "EMP-RELOAD",
            "employee_name": "Reload Employee",
            "employee_code": "E-RELOAD",
        },
    )
    assert response.status_code == 201

    for _ in range(5):
        response = client.post(
            "/api/v1/face/enroll/sample",
            json={"employee_id": "EMP-RELOAD", "image_base64": image_base64},
        )
        assert response.status_code == 201
        assert response.json()["data"]["accepted"] is True

    response = client.post(
        "/api/v1/face/enroll/finish",
        json={"employee_id": "EMP-RELOAD"},
    )
    assert response.status_code == 200

    faiss_service.clear()

    response = client.post(
        "/api/v1/attendance/checkin",
        json={"image_base64": image_base64},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["matched"] is True
    assert payload["employee_id"] == "EMP-RELOAD"
