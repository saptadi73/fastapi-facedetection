# TODO Implementasi Face Detection + Odoo HR Attendance

Dokumen ini menjadi daftar kerja aktif berdasarkan dokumentasi arsitektur,
roadmap inferensi, dan kondisi repository saat ini.

## Sudah dikerjakan sekarang

- [x] Menambahkan `venv/`, `.env`, `.pyc`, dan `__pycache__/` ke `.gitignore`.
- [x] Menambahkan integrasi attendance Odoo 14 melalui JSON-RPC:
  `hr.attendance` create untuk check-in dan write untuk checkout.
- [x] Menambahkan validasi open attendance di Odoo agar check-in ganda ditolak.
- [x] Mengganti upload attachment placeholder dengan `ir.attachment` JSON-RPC.
- [x] Menambahkan pencegahan duplicate attendance lokal berdasarkan employee,
  action, dan window waktu.
- [x] Menambahkan mode mock eksplisit untuk test/development tanpa Odoo.
- [x] Menambahkan endpoint `POST /api/v1/attendance/sync/retry` untuk replay
  sinkronisasi Odoo yang gagal.
- [x] Menambahkan worker retry periodik yang dapat diaktifkan melalui environment.
- [x] Menambahkan idempotency `event_id` agar retry frontend tidak membuat
  attendance Odoo ganda.
- [x] Menambahkan API key opsional untuk endpoint enrollment, attendance,
  device, dan retry Odoo.
- [x] Menjadikan penyimpanan foto ke Odoo attachment opt-in; default hanya
  local/object storage.

## Prioritas berikutnya

### P0 — wajib sebelum pilot HR

- [ ] Isi konfigurasi service user Odoo melalui secret manager atau environment:
  `ODOO_INTEGRATION_ENABLED=true`, `ODOO_BASE_URL`, `ODOO_DB`,
  `ODOO_USERNAME`, dan `ODOO_PASSWORD`/API key.
- [ ] Uji JSON-RPC pada database Odoo staging: check-in, checkout, duplicate,
  employee tidak ditemukan, timeout, dan SSL.
- [x] Buat custom module Odoo `grt_face_attendance_bridge` untuk validasi radius
  GPS, audit event, dan idempotency `event_id` server-side.
- [x] Tambahkan jalur FastAPI ke endpoint bridge dengan API key. Jalur JSON-RPC
  langsung tetap menjadi fallback staging ketika API key bridge belum diisi.
- [ ] Deploy dan instal `grt_face_attendance_bridge` pada database staging.
- [ ] Isi lokasi/radius, toleransi akurasi GPS, URL FastAPI, dan API key dari
  Odoo Settings; gunakan secret yang sama pada `ODOO_ATTENDANCE_API_KEY`.
- [ ] Uji worker retry terhadap Odoo staging dengan timeout/network failure.
- [ ] Ganti API key bersama dengan JWT/service identity bila deployment sudah
  memiliki identity provider; HTTPS tetap wajib.

### P1 — kualitas recognition

- [ ] Ganti detector placeholder dengan MediaPipe face detection/landmark nyata.
- [ ] Aktifkan model embedding ONNX production dan kalibrasi threshold dengan
  dataset pilot yang disetujui HR.
- [ ] Validasi pose, single-face, blur, brightness, dan liveness/anti-spoofing.
- [ ] Persist/rebuild index recognition dengan FAISS native setelah skala template
  melebihi kebutuhan in-memory.

### P2 — operasional dan UX

- [ ] Sediakan frontend Vue untuk enrollment multi-sample, attendance, GPS, dan
  feedback reason code.
- [ ] Tambahkan metric latency, similarity, reject reason, dan success rate Odoo.
- [ ] Tambahkan retention policy untuk foto/embedding dan audit akses biometric.
- [ ] Jalankan UAT lintas device/site serta benchmark p95 sebelum rollout.

## Catatan konfigurasi

Tanpa konfigurasi Odoo, development/test memakai mock jika
`ODOO_ALLOW_MOCK=true` (default). Untuk staging/production, aktifkan integrasi
JSON-RPC dan matikan mock:

```env
ODOO_INTEGRATION_ENABLED=true
ODOO_ALLOW_MOCK=false
ODOO_BASE_URL=https://odoo.example.com
ODOO_DB=odoo_prod
ODOO_USERNAME=face-attendance-service
ODOO_PASSWORD=<secret>
ODOO_ATTENDANCE_ENDPOINT=/api/face-attendance/event
ODOO_ATTENDANCE_API_KEY=<same-secret-as-odoo-settings>
ODOO_VERIFY_SSL=true
```
