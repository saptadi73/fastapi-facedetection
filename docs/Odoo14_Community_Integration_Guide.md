# Odoo 14 Community Integration Guide

Dokumen ini menjadi referensi teknis implementasi integrasi antara layanan
FastAPI Face Attendance dengan Odoo 14 Community.

## 1. Tujuan Integrasi

Integrasi Odoo bertujuan untuk:

- memetakan employee Odoo ke identitas wajah di FastAPI
- menerima hasil matching check-in/check-out dari FastAPI
- menerima koordinat GPS saat attendance
- menerapkan validasi radius lokasi attendance yang dikelola di Odoo
- menyimpan evidence attachment foto bila diperlukan
- menjaga HR attendance di Odoo sebagai system of record

## 2. Arsitektur Integrasi

```text
[Vue Frontend] -> [FastAPI Face Service] -> [Odoo 14 Community]
                                      \-> [PostgreSQL Face DB]
                                      \-> [Local/Object Storage]
```

Arus data utama:

1. Enrollment dimulai dari frontend dan diproses di FastAPI.
2. FastAPI menyimpan sample, template, dan metadata storage.
3. Saat attendance sukses, FastAPI memanggil Odoo untuk create/update attendance.
4. Odoo memvalidasi rule bisnis, termasuk radius GPS jika diaktifkan.
5. Odoo menyimpan attendance final untuk kebutuhan HR dan reporting.

## 2.1 Status Implementasi Backend Saat Ini

Bagian yang sudah tersedia di repository `fastapi-fd`:

- attendance request sudah mendukung field GPS
- data GPS sudah disimpan pada tabel `face_attendance_attempt`
- payload sinkronisasi ke Odoo sudah menyertakan konteks GPS
- helper geolocation untuk hitung jarak meter sudah tersedia
- enrollment sudah mendukung multi-foto dan multi-template per employee
- embedding provider dapat berupa `visual` atau `onnx`
- model `.onnx` bersifat statis; upload foto employee tidak mengubah model
- attachment upload ke Odoo masih berupa placeholder service

Bagian yang masih perlu diimplementasikan di Odoo:

- model master lokasi attendance
- validasi radius lokasi
- endpoint/controller Odoo yang memutuskan accepted/rejected
- penyimpanan hasil validasi lokasi pada attendance atau event log

## 3. Prasyarat Odoo 14

- modul `hr` dan `hr_attendance` aktif
- user teknis integrasi dengan akses minimum:
  - read `hr.employee`
  - create/read/write `hr.attendance`
  - create/read `ir.attachment` bila evidence foto diaktifkan
- endpoint Odoo bisa diakses dari host FastAPI
- HTTPS direkomendasikan untuk seluruh traffic integrasi

## 4. Konfigurasi yang Disarankan di FastAPI

Contoh environment variable:

```env
ODOO_BASE_URL=https://odoo.example.com
ODOO_DB=odoo_prod
ODOO_USERNAME=face.integration@company.com
ODOO_PASSWORD=your-password
ODOO_TIMEOUT_SECONDS=15
ODOO_VERIFY_SSL=true
ODOO_ATTACHMENTS_ENABLED=true
ODOO_ATTACHMENT_MODEL=hr.attendance
```

Catatan:

- jangan commit credential ke repository
- gunakan secret manager atau environment deployment
- konfigurasi face model seperti `FACE_EMBEDDING_PROVIDER` dan `FACE_ONNX_MODEL_PATH` berada di FastAPI, bukan di Odoo

## 5. Desain Mapping Data

### 5.1 Mapping Employee

Gunakan tabel `face_employee_map` di FastAPI untuk referensi employee Odoo.

Rekomendasi mapping:

- `face_employee_map.employee_id` -> `hr.employee.id`
- `face_employee_map.employee_code` -> `hr.employee.barcode` atau `identification_id`
- `face_employee_map.employee_name` -> `hr.employee.name`

### 5.2 Attendance Result

Saat FastAPI match sukses:

- `action=checkin` -> create row baru di `hr.attendance`
- `action=checkout` -> update `check_out` pada attendance aktif employee

Log sinkronisasi disimpan di `odoo_attendance_sync`.

Field biometric yang perlu dipahami Odoo:

- Odoo menerima hasil akhir matching, bukan menjalankan model face recognition.
- `embedding_provider` dapat dikirim sebagai metadata audit (`visual` atau `onnx`).
- FastAPI response attendance membedakan hasil biometric match dari status sinkronisasi Odoo melalui `odoo_sync_status`.
- Foto enrollment/attendance dapat disimpan sebagai evidence attachment bila diaktifkan.
- Embedding/template wajah sebaiknya tetap berada di database FastAPI, bukan disalin ke Odoo.
- Jika model `.onnx` diganti, semua employee perlu enrollment ulang di FastAPI.

### 5.3 GPS dan Radius Attendance

FastAPI saat ini menerima dan menyimpan field GPS berikut pada setiap attendance attempt:

- `latitude`
- `longitude`
- `gps_accuracy_meters`
- `gps_provider`

Rekomendasi desain di Odoo 14:

- buat master lokasi attendance
- simpan titik pusat (`latitude`, `longitude`)
- simpan radius yang diizinkan dalam meter
- saat event masuk, hitung jarak dari titik absensi ke titik pusat
- tolak attendance jika jarak melebihi radius yang diizinkan

Field tambahan yang direkomendasikan untuk model lokasi:

- `gps_accuracy_tolerance_meters`
- `attendance_type` (`checkin`, `checkout`, `both`)
- `site_code`
- `note`

### 5.4 Evidence Attachment

Metadata evidence tersimpan di `face_sample_storage` dengan target `odoo`.

Implementasi attachment Odoo:

- model `ir.attachment`
- `res_model` -> `hr.attendance` atau model custom log
- `res_id` -> id record attendance/log terkait
- `datas` -> base64 image
- `mimetype` -> `image/png`

## 6. Opsi Implementasi di Odoo

### Opsi A: Tanpa Modul Custom

Gunakan XML-RPC/JSON-RPC langsung ke model standar:

- read employee (`hr.employee`)
- create/update attendance (`hr.attendance`)
- create attachment (`ir.attachment`)

Kelebihan:

- implementasi cepat
- perubahan Odoo minimal

Kekurangan:

- logic bisnis radius dan validasi tersebar
- audit trail event lebih sulit dirapikan

### Opsi B: Dengan Modul Custom Odoo

Disarankan membuat modul misalnya `face_attendance_bridge`.

Tanggung jawab modul:

- menyediakan endpoint inbound attendance
- memvalidasi radius GPS
- memvalidasi duplicate checkin/checkout
- menyimpan audit trail event

Struktur modul minimal:

```text
face_attendance_bridge/
├── __manifest__.py
├── controllers/
│   └── api.py
├── models/
│   ├── face_event_log.py
│   ├── hr_attendance_inherit.py
│   └── attendance_location.py
├── security/
│   └── ir.model.access.csv
└── data/
    └── ir_config_parameter.xml
```

## 7. Spesifikasi API Kontrak FastAPI ke Odoo

Contoh payload:

```json
{
  "event_id": "uuid-or-attempt-id",
  "employee_id": "123",
  "action": "checkin",
  "captured_at": "2026-07-08T09:00:00Z",
  "similarity": 0.92,
  "embedding_provider": "onnx",
  "device_code": "CAM-001",
  "quality_score": 3500.12,
  "latitude": -6.1753924,
  "longitude": 106.8271528,
  "gps_accuracy_meters": 8.75,
  "gps_provider": "browser",
  "photo": {
    "local_url": "/uploads/local/EMP001/sample_10.png",
    "object_url": "https://face.example.com/uploads/object/EMP001/sample_10.png",
    "odoo_attachment_id": null
  }
}
```

Contoh response sukses:

```json
{
  "success": true,
  "attendance_id": 4567,
  "status": "created",
  "message": "Check-in recorded",
  "location_validation": {
    "valid": true,
    "distance_meters": 12.4,
    "allowed_radius_meters": 50,
    "location_name": "Head Office"
  }
}
```

Contoh response jika lokasi di luar radius:

```json
{
  "success": false,
  "status": "rejected",
  "message": "Location outside allowed radius",
  "location_validation": {
    "valid": false,
    "distance_meters": 143.2,
    "allowed_radius_meters": 50,
    "location_name": "Head Office"
  }
}
```

## 8. Logic Attendance yang Harus Dijaga

- checkin hanya jika tidak ada attendance open
- checkout hanya jika ada attendance open
- duplicate window untuk debounce
- idempotency berdasarkan `event_id`
- radius validation berdasarkan lokasi attendance Odoo
- optional tolerance berdasarkan `gps_accuracy_meters`

Contoh rule radius:

1. tentukan lokasi attendance aktif untuk employee atau site
2. hitung jarak antara GPS request dan titik pusat lokasi Odoo
3. jika `distance_meters <= allowed_radius_meters`, attendance boleh lanjut
4. jika lebih besar, return error validasi lokasi

Rekomendasi model custom:

`face.attendance.location`

- `name`
- `latitude`
- `longitude`
- `allowed_radius_meters`
- `company_id`
- `active`

Rekomendasi model log event:

`face.attendance.event.log`

- `event_id`
- `employee_id`
- `attendance_id`
- `latitude`
- `longitude`
- `gps_accuracy_meters`
- `distance_meters`
- `radius_allowed_meters`
- `location_validation_status`
- `raw_payload`

## 9. Keamanan Integrasi

Minimal:

- HTTPS end-to-end
- API key atau JWT antar FastAPI dan Odoo endpoint custom
- rotate credential service user
- whitelist source IP jika memungkinkan

Rekomendasi tambahan:

- sign payload dengan HMAC
- audit log request/response tanpa menyimpan secret

Catatan biometric dan lisensi model:

- Foto wajah dan embedding adalah data sensitif; batasi akses, audit penggunaan, dan tetapkan retention policy.
- Pastikan ada dasar persetujuan/pemberitahuan karyawan sesuai kebijakan perusahaan dan regulasi yang berlaku.
- Model ONNX pihak ketiga harus dicek lisensinya sebelum digunakan untuk production/komersial.
- InsightFace pretrained model umum digunakan untuk riset/non-commercial; production komersial perlu lisensi/model yang sesuai.

## 10. Error Handling dan Retry

Klasifikasi error:

- 4xx: error data atau validasi, tidak perlu retry agresif
- 5xx/network timeout: retry dengan exponential backoff

Skema retry yang disarankan:

- attempt ke-1 langsung
- attempt ke-2 delay 2 detik
- attempt ke-3 delay 5 detik
- jika tetap gagal, tandai `sync_status=failed` dan masuk antrean reprocess

## 11. Rekonsiliasi Data

Jalankan job periodik, misalnya tiap 15 menit:

- ambil `odoo_attendance_sync` status failed atau pending
- replay sinkronisasi berdasarkan `attempt_id`
- update status sukses atau gagal akhir

## 12. Checklist UAT Integrasi Odoo

- employee valid dapat checkin
- employee valid dapat checkout
- duplicate checkin ditolak sesuai rule
- attendance dengan GPS di dalam radius diterima
- attendance dengan GPS di luar radius ditolak
- attendance dengan akurasi GPS buruk diperlakukan sesuai rule bisnis
- attendance di Odoo muncul sesuai timezone
- attachment foto terbentuk bila enabled
- metadata `embedding_provider` tercatat bila dikirim sebagai audit
- kegagalan Odoo menghasilkan log gagal di FastAPI
- replay job dapat memperbaiki status gagal

## 13. Rencana Implementasi Bertahap

Tahap 1:

- sinkronisasi checkin/checkout
- simpan payload GPS
- tampilkan hasil radius validation

Tahap 2:

- aktifkan attachment foto
- aktifkan retry dan reprocess job

Tahap 3:

- modul custom Odoo dengan endpoint bridge
- idempotency server-side
- dashboard audit event lokasi

## 14. Catatan Praktis untuk Kode Saat Ini

File backend yang terkait langsung:

- `services/odoo_service.py`
- `services/geolocation_service.py`
- `routes/attendance.py`
- `routes/face_enrollment.py`
- `models/face_attendance.py`

Langkah lanjutan paling dekat:

1. ganti placeholder `upload_face_attachment` dengan XML-RPC/JSON-RPC Odoo nyata
2. tambahkan endpoint atau modul radius validation di Odoo
3. ikat `odoo_attachment_id` ke `hr.attendance` atau event log
4. tambahkan worker retry untuk `odoo_attendance_sync`

Roadmap migrasi inferensi end-to-end tersedia di:

- `docs/Inference_Pipeline_Roadmap.md`
