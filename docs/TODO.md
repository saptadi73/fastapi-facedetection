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
- [x] Menambahkan access token JWT FastAPI untuk frontend; session Odoo tidak
  dikembalikan ke browser.
- [x] Menambahkan CORS terkonfigurasi melalui `BACKEND_CORS_ORIGINS` untuk Vue.

## Prioritas berikutnya

### P0 — wajib sebelum pilot HR

- [ ] Isi konfigurasi client JWT Odoo melalui secret manager atau environment:
  `ODOO_INTEGRATION_ENABLED=true`, `ODOO_BASE_URL`, `ODOO_DB`,
  `ODOO_API_MODE=external`, `ODOO_EXTERNAL_API_CLIENT_ID`, dan
  `ODOO_EXTERNAL_API_CLIENT_SECRET`.
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
- [x] Gunakan JWT `grt_external_api` dengan scope HR; self-service dibatasi ke
  employee milik user Odoo, sedangkan akses lintas employee memerlukan scope
  `hr:admin`.
- [x] Dokumentasikan kontrak JWT, scope HR, endpoint Odoo, dan konfigurasi
  client pada panduan integrasi.
- [ ] Ganti client secret dengan secret manager dan aktifkan request signature
  HMAC bila diwajibkan oleh client Odoo; HTTPS tetap wajib.
- [ ] Aktifkan `FRONTEND_AUTH_ENABLED=true` di staging/production dan isi
  `JWT_SECRET_KEY` melalui secret manager.
- [ ] Uji login Vue, bearer token expired/invalid, CORS preflight, dan logout
  pada environment staging.
- [x] Tambahkan authorization berbasis claim `employee_id` pada endpoint
  self-service Time Off, Overtime, dan daftar Payslip agar user tidak dapat
  mengirim employee lain secara manual.
- [x] Tambahkan validasi ownership untuk cancel Time Off dan download payslip
  individual pada mode frontend JWT.
- [x] Tambahkan claim `is_hr_admin` dari group Odoo HR Manager/Payroll Manager
  agar HR dapat mengakses employee lain secara terkontrol.
- [ ] Uji role HR admin pada database Odoo staging dan batasi client JWT Odoo
  dengan scope `hr:admin`.
- [ ] Validasi delegated user context pada mode `ODOO_API_MODE=external`;
  token service Odoo harus tetap dapat mengotorisasi employee user Vue tanpa
  mempercayai `employee_id` mentah dari browser.

### P1 — kualitas recognition

- [x] Menambahkan MediaPipe Face Mesh untuk landmark dan estimasi pose yaw/pitch/roll.
- [x] Menambahkan batas pose pada quality gate melalui `FACE_MAX_YAW`,
  `FACE_MAX_PITCH`, dan `FACE_MAX_ROLL`.
- [x] Menambahkan baseline metrics request, HTTP status, endpoint count, dan
  average latency melalui `GET /metrics`.
- [x] Menambahkan readiness check embedding pada `/health`; provider ONNX yang
  gagal tidak lagi dilaporkan sebagai healthy.
- [x] Menambahkan endpoint FastAPI untuk Time Off, Overtime, daftar Payslip,
  dan download PDF Payslip melalui koneksi Odoo JSON-RPC.
- [x] Menambahkan adapter detector OpenCV Haar Cascade sebagai baseline CPU
  yang dapat diaktifkan dengan `FACE_DETECTOR_PROVIDER=opencv`.
- [x] Menambahkan provider MediaPipe Face Detection yang dapat diaktifkan dengan
  `FACE_DETECTOR_PROVIDER=mediapipe`.
- [ ] Aktifkan model embedding ONNX production dan kalibrasi threshold dengan
  dataset pilot yang disetujui HR. Readiness check sudah tersedia.
- [ ] Validasi pose, single-face, blur, brightness, dan liveness/anti-spoofing.
- [x] Persist/rebuild cache index recognition dari `face_template` saat startup.
- [ ] Ganti cache nearest-neighbor dengan FAISS native setelah skala template
  melebihi kebutuhan in-memory.

### P2 — operasional dan UX

- [ ] Sediakan frontend Vue untuk enrollment multi-sample, attendance, GPS,
  Time Off, Overtime, Payslip, dan feedback reason code.
- [ ] Tambahkan metric similarity, reject reason, dan success rate Odoo per
  employee/device/site; baseline HTTP metrics sudah tersedia.
- [ ] Tambahkan retention policy untuk foto/embedding dan audit akses biometric.
- [ ] Jalankan UAT lintas device/site serta benchmark p95 sebelum rollout.

## Catatan konfigurasi

Tanpa konfigurasi Odoo, development/test memakai mock jika
`ODOO_ALLOW_MOCK=true` (default). Untuk staging/production, aktifkan integrasi
JWT external API dan matikan mock:

```env
ODOO_INTEGRATION_ENABLED=true
ODOO_ALLOW_MOCK=false
ODOO_BASE_URL=https://odoo.example.com
ODOO_DB=odoo_prod
ODOO_API_MODE=external
ODOO_EXTERNAL_API_CLIENT_ID=fastapi-facedetection
ODOO_EXTERNAL_API_CLIENT_SECRET=<secret>
ODOO_EXTERNAL_API_SCOPES=hr:attendance:write,hr:timeoff:read,hr:timeoff:write,hr:overtime:read,hr:overtime:write,hr:payroll:read
ODOO_ATTENDANCE_ENDPOINT=/api/face-attendance/event
ODOO_VERIFY_SSL=true
```
