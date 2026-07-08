from __future__ import annotations

import base64
import io


def _build_image_base64() -> str:
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

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "fastapi-fd"
    assert payload["healthy"] is True


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


def test_enrollment_and_checkin_flow(client):
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

    response = client.post(
        "/api/v1/attendance/checkin",
        json={
            "device_code": "CAM-T1",
            "image_base64": image_base64,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["matched"] is True
    assert payload["data"]["employee_id"] == "EMP-T1"
    assert payload["data"]["status"] == "success"
