# Production Deployment Runbook

## Komponen

- FastAPI: `/var/www/fastapi_app`, service `api-facedetection`.
- Vue: `/var/www/facedetection`, domain `https://hris.kanjabung.com`.
- Odoo: modul `grt_face_attendance_bridge`, database `odoo_prod`.

## Urutan deployment

1. Backup source/service dan database.
2. Deploy dan upgrade modul Odoo.
3. Jalankan `alembic upgrade head` pada FastAPI.
4. Restart FastAPI dan cek `/health`.
5. Build Vue dengan type-check lalu publish `dist`.
6. Uji login, kamera, GPS, presensi kantor, dan kunjungan.

## Upgrade Odoo

```bash
sudo systemctl stop odoo14
sudo -u odoo /opt/odoo14/odoo/odoo-bin -c /etc/odoo14.conf \
  -d odoo_prod -u grt_face_attendance_bridge --stop-after-init
sudo systemctl start odoo14
sudo systemctl is-active odoo14
```

Gunakan user runtime yang tertera pada `systemctl cat odoo14` bila bukan `odoo`.

## Upgrade FastAPI

```bash
cd /var/www/fastapi_app
sudo -u saptadi /var/www/fastapi_app/.venv/bin/alembic upgrade head
sudo systemctl restart api-facedetection
curl -fsS https://hris.kanjabung.web.id/health
```

Migration `20261015_0007` menambah konteks attendance dan detail kunjungan.

## Verifikasi

- `/health` mengembalikan `healthy: true`.
- OpenAPI AttendanceRequest memiliki `attendance_context`, `visit_partner`, dan `visit_note`.
- Bundle frontend terbaru memuat pilihan Kantor/Kunjungan.
- Log Odoo tidak menunjukkan error model/view.
- Admin dapat membuat group dan Home Point.

## Rollback

Kembalikan source dari backup, restore database bila diperlukan, restart service,
lalu ulangi smoke test. Simpan waktu, operator, versi build, dan hasil health check.
