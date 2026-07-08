# Odoo 14 Community Integration Guide

Dokumen ini adalah panduan teknis implementasi integrasi antara layanan FastAPI Face Attendance dengan Odoo 14 Community.

## 1. Tujuan Integrasi

Integrasi Odoo bertujuan untuk:

- memetakan identitas employee Odoo ke face identity di FastAPI
- menerima hasil matching check-in/check-out dari FastAPI
- menyimpan evidence attachment foto (opsional, dapat diaktifkan bertahap)
- menjaga konsistensi status attendance antara dua sistem

## 2. Arsitektur Integrasi

```text
[Vue Frontend] -> [FastAPI Face Service] -> [Odoo 14 Community]
                                      \-> [PostgreSQL Face DB]
                                      \-> [Local/Object Storage]
```

Arus data utama:

1. Enrollment dimulai dari frontend/FastAPI.
2. FastAPI menyimpan sample, template, dan metadata storage.
3. Saat attendance sukses, FastAPI memanggil API Odoo untuk create/update attendance.
4. Odoo menyimpan catatan HR attendance sebagai system of record untuk HR.

## 3. Prasyarat Odoo 14

- Odoo 14 Community aktif dengan modul `hr` dan `hr_attendance`
- user teknis integrasi (service user) dengan akses minimum:
  - read `hr.employee`
  - create/read/write `hr.attendance`
  - create/read `ir.attachment` (jika evidence foto diaktifkan)
- endpoint Odoo dapat diakses dari host FastAPI (HTTPS direkomendasikan)

## 4. Konfigurasi yang Disarankan di FastAPI

Tambahkan variabel environment berikut (contoh):

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

## 5. Desain Mapping Data

### 5.1 Mapping Employee

Gunakan table `face_employee_map` di FastAPI untuk referensi employee Odoo.

Rekomendasi field mapping:

- `face_employee_map.employee_id` -> `hr.employee.id` (string/ID)
- `face_employee_map.employee_code` -> `hr.employee.barcode` atau `identification_id`
- `face_employee_map.employee_name` -> `hr.employee.name`

### 5.2 Attendance Result

Saat FastAPI match sukses:

- `action=checkin` -> create row baru di `hr.attendance`
- `action=checkout` -> update `check_out` row attendance aktif employee

Log sinkronisasi disimpan di `odoo_attendance_sync`.

### 5.3 Evidence Attachment (Opsional)

Metadata evidence tersimpan di `face_sample_storage` dengan target `odoo`.

Implementasi Odoo attachment:

- model `ir.attachment`
- `res_model` -> `hr.attendance` (atau model custom)
- `res_id` -> id attendance yang dibuat/update
- `datas` -> base64 image
- `mimetype` -> `image/png`

## 6. Opsi Implementasi di Odoo

## Opsi A: Tanpa Modul Custom (Cepat)

Gunakan XML-RPC/JSON-RPC langsung ke model standar:

- read employee (`hr.employee`)
- create/update attendance (`hr.attendance`)
- create attachment (`ir.attachment`)

Kelebihan:

- implementasi cepat
- minim maintenance modul Odoo

Kekurangan:

- logic bisnis tersebar di FastAPI

## Opsi B: Dengan Modul Custom Odoo (Direkomendasikan)

Buat modul Odoo misalnya `face_attendance_bridge`:

- endpoint controller internal Odoo untuk inbound event
- centralisasi business rule di Odoo
- validasi duplicate checkin/checkout di server Odoo
- audit trail tambahan

Struktur modul minimal:

```text
face_attendance_bridge/
├── __manifest__.py
├── controllers/
│   └── api.py
├── models/
│   ├── face_event_log.py
│   └── hr_attendance_inherit.py
├── security/
│   └── ir.model.access.csv
└── data/
    └── ir_config_parameter.xml
```

## 7. Spesifikasi API Kontrak (FastAPI -> Odoo)

Gunakan payload kontrak stabil berikut:

```json
{
  "event_id": "uuid-or-attempt-id",
  "employee_id": "123",
  "action": "checkin",
  "captured_at": "2026-07-08T09:00:00Z",
  "similarity": 0.92,
  "device_code": "CAM-001",
  "quality_score": 3500.12,
  "photo": {
    "local_url": "/uploads/local/EMP001/sample_10.png",
    "object_url": "https://face.example.com/uploads/object/EMP001/sample_10.png",
    "odoo_attachment_id": null
  }
}
```

Respons yang disarankan dari Odoo:

```json
{
  "success": true,
  "attendance_id": 4567,
  "status": "created",
  "message": "Check-in recorded"
}
```

## 8. Logic Attendance yang Harus Dijaga

- checkin hanya jika tidak ada attendance open
- checkout hanya jika ada attendance open
- duplicate window (misalnya 30-120 detik) untuk debounce
- idempotency berdasarkan `event_id` untuk menghindari double post

## 9. Keamanan Integrasi

Minimal:

- HTTPS end-to-end
- API key atau JWT antar FastAPI dan Odoo endpoint custom
- rotate credential service user berkala
- whitelist source IP jika memungkinkan

Rekomendasi tambahan:

- sign payload (HMAC)
- audit log request/response (tanpa secret)

## 10. Error Handling dan Retry

Klasifikasi error:

- 4xx: error data/validasi, tidak perlu retry agresif
- 5xx/network timeout: retry dengan exponential backoff

Skema retry yang disarankan:

- attempt ke-1 langsung
- attempt ke-2 delay 2 detik
- attempt ke-3 delay 5 detik
- jika tetap gagal, tandai `sync_status=failed` dan masuk antrean reprocess

## 11. Rekonsiliasi Data

Jalankan job periodik (mis. tiap 15 menit):

- ambil `odoo_attendance_sync` status failed/pending
- replay sinkronisasi berdasarkan `attempt_id`
- update status sukses/gagal akhir

## 12. Checklist UAT Integrasi Odoo

- employee valid dapat checkin
- employee valid dapat checkout
- duplicate checkin ditolak sesuai rule
- attendance di Odoo muncul sesuai timezone
- attachment foto terbentuk (jika enabled)
- kegagalan Odoo menghasilkan log gagal di FastAPI
- replay job dapat memperbaiki status gagal

## 13. Rencana Implementasi Bertahap

Tahap 1:

- sinkronisasi checkin/checkout tanpa attachment

Tahap 2:

- aktifkan attachment foto
- aktifkan retry + reprocess job

Tahap 3:

- modul custom Odoo dengan endpoint bridge + idempotency server-side

## 14. Catatan Praktis untuk Kode Saat Ini

Pada repository ini, method upload attachment di service Odoo masih placeholder.

File terkait:

- `services/odoo_service.py`
- `routes/face_enrollment.py`
- `models/face_attendance.py` (table `face_sample_storage`)

Langkah lanjutan paling dekat:

1. ganti placeholder `upload_face_attachment` dengan call XML-RPC/JSON-RPC Odoo nyata
2. ikat `odoo_attachment_id` ke `hr.attendance` setelah checkin/checkout sukses
3. tambahkan worker retry untuk `odoo_attendance_sync`
