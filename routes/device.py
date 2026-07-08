from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.database import get_db
from models.face_attendance import FaceDevice
from schemas.device import DeviceCreateRequest
from supports import error_response, success_response

router = APIRouter(prefix="/api/v1/device", tags=["Device"])


@router.get("")
def list_devices(db: Session = Depends(get_db)):
    devices = db.scalars(select(FaceDevice).order_by(FaceDevice.id.desc())).all()
    items = [
        {
            "id": item.id,
            "device_code": item.device_code,
            "device_name": item.device_name,
            "location": item.location,
            "is_active": item.is_active,
            "last_seen_at": item.last_seen_at.isoformat() if item.last_seen_at else None,
        }
        for item in devices
    ]

    return success_response(
        message="Devices fetched",
        code="DEVICE_LIST",
        data={"items": items, "total": len(items)},
    )


@router.post("")
def create_device(payload: DeviceCreateRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(FaceDevice).where(FaceDevice.device_code == payload.device_code))
    if existing is not None:
        return error_response(
            message="Device code already exists",
            status_code=409,
            code="DEVICE_EXISTS",
        )

    device = FaceDevice(
        device_code=payload.device_code,
        device_name=payload.device_name,
        location=payload.location,
        is_active=True,
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    return success_response(
        message="Device created",
        status_code=201,
        code="DEVICE_CREATED",
        data={
            "id": device.id,
            "device_code": device.device_code,
            "device_name": device.device_name,
            "location": device.location,
            "is_active": device.is_active,
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        },
    )
