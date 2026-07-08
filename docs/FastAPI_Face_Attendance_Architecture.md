# Face Attendance Service Architecture (FastAPI + OpenCV + MediaPipe)

## Tujuan

Dokumen ini menjadi referensi implementasi backend **Face Attendance
Service** yang berjalan terpisah dari Odoo 14 Community.

Arsitektur:

``` text
Vue 3 + OpenCV.js
        |
        v
 FastAPI Face Service
        |
  OpenCV Python
        |
   MediaPipe
        |
 Recognition Engine
        |
     FAISS
        |
      Odoo 14
```

## Tanggung Jawab

### Frontend

-   Capture webcam
-   Quality check awal (blur, brightness)
-   Crop & compress
-   Kirim gambar ke FastAPI

### FastAPI

-   Validasi request
-   OpenCV preprocessing
-   MediaPipe face detection
-   Landmark & quality validation
-   Generate embedding
-   Matching menggunakan FAISS
-   Sinkronisasi attendance ke Odoo

### Odoo

-   Master Employee
-   HR Attendance
-   Approval & Reporting

------------------------------------------------------------------------

# Struktur Modul

``` text
app/
├── api/
├── core/
├── database.py
├── models/
│   └── face_attendance.py
├── schemas/
├── services/
│   ├── camera_service.py
│   ├── image_service.py
│   ├── mediapipe_service.py
│   ├── embedding_service.py
│   ├── faiss_service.py
│   ├── attendance_service.py
│   └── odoo_service.py
├── repositories/
├── utils/
└── main.py
```

------------------------------------------------------------------------

# Database

Tabel utama:

-   face_employee_map
-   face_enrollment
-   face_sample
-   face_sample_storage
-   face_template
-   face_attendance_attempt
-   face_detection_result
-   face_recognition_result
-   odoo_attendance_sync
-   face_device
-   face_setting

Relasi:

``` text
face_employee_map
 ├── face_enrollment
 │      └── face_sample
 │             └── face_sample_storage
 ├── face_template
 └── odoo_attendance_sync

face_attendance_attempt
 ├── face_detection_result
 ├── face_recognition_result
 └── odoo_attendance_sync
```

------------------------------------------------------------------------

# Workflow Enrollment

1.  Odoo memilih employee.
2.  Frontend mengambil 10--20 foto dari berbagai sudut.
3.  FastAPI:
    -   OpenCV preprocessing
    -   MediaPipe detection
    -   Quality validation
4.  Simpan face_sample.
5.  Generate embedding.
6.  Simpan face_template.
7.  Update status enrollment.

------------------------------------------------------------------------

# Workflow Attendance

1.  Capture webcam.
2.  Ambil koordinat GPS device/browser.
3.  Frontend preprocessing.
4.  Upload image + GPS ke FastAPI.
5.  OpenCV preprocessing ulang.
6.  MediaPipe mendeteksi wajah.
7.  Validasi:
    -   hanya 1 wajah
    -   blur
    -   brightness
    -   pose
8.  Generate embedding.
9.  Cari kandidat menggunakan FAISS.
10. Jika similarity memenuhi threshold:
    -   create/update attendance Odoo.
11. Kirim GPS ke Odoo untuk validasi radius lokasi.
12. Simpan audit log.

------------------------------------------------------------------------

# Service Layer

## image_service

-   resize
-   crop
-   rotate
-   blur detection
-   brightness
-   histogram
-   image normalization

## mediapipe_service

-   face detection
-   landmark
-   face mesh
-   head pose

## embedding_service

-   generate embedding
-   compare embedding

## faiss_service

-   build index
-   add embedding
-   update embedding
-   remove embedding
-   nearest neighbor search

## attendance_service

-   validasi check-in/out
-   duplicate detection
-   business rules

## odoo_service

-   authenticate
-   create attendance
-   update checkout
-   synchronize employee
-   upload face attachment

## local_storage_service

-   simpan file foto ke `uploads/local`
-   baca ulang file foto untuk proses embedding

## object_storage_service

-   simpan file foto ke `uploads/object`
-   hasilkan object-style public URL

## sample_media_storage_service

-   orkestrasi simpan ke local + object + Odoo attachment
-   kembalikan metadata storage untuk disimpan ke database

## geolocation_service

-   normalisasi payload GPS attendance
-   helper hitung jarak meter antar koordinat
-   fondasi validasi radius attendance

------------------------------------------------------------------------

# REST API

## Enrollment

POST /api/v1/face/enroll/start

POST /api/v1/face/enroll/sample

POST /api/v1/face/enroll/finish

GET /api/v1/face/enroll/{employee_id}

## Attendance

POST /api/v1/attendance/checkin

POST /api/v1/attendance/checkout

GET /api/v1/attendance/history

Contoh payload attendance:

``` json
{
    "device_code": "CAM-001",
    "image_base64": "<base64>",
    "latitude": -6.1753924,
    "longitude": 106.8271528,
    "gps_accuracy_meters": 8.75,
    "gps_provider": "browser"
}
```

## Device

GET /api/v1/device

POST /api/v1/device

## Health

GET /health

------------------------------------------------------------------------

# Quality Rules

-   Tepat satu wajah.
-   Confidence detector \>= konfigurasi.
-   Blur memenuhi batas minimum.
-   Brightness dalam rentang yang diterima.
-   Pose (yaw/pitch/roll) masih dalam toleransi.

------------------------------------------------------------------------

# Integrasi Odoo

Saat match berhasil:

1.  Cari employee berdasarkan mapping.
2.  Tentukan check-in atau check-out.
3.  Panggil endpoint Odoo.
4.  Simpan hasil sinkronisasi pada odoo_attendance_sync.

------------------------------------------------------------------------

# Konfigurasi

Contoh pengaturan:

-   recognition_threshold
-   min_detection_confidence
-   min_blur_score
-   min_brightness_score
-   max_face_count
-   attendance_duplicate_window

------------------------------------------------------------------------

# Keamanan

-   HTTPS wajib.
-   JWT antar frontend dan FastAPI.
-   API Key untuk komunikasi ke Odoo.
-   Audit seluruh percobaan.
-   Simpan embedding, bukan password atau data biometrik mentah sebagai
    identitas login.
-   Batasi akses endpoint administrasi.

------------------------------------------------------------------------

# Roadmap

Phase 1 - OpenCV - MediaPipe - Enrollment - Attendance - Odoo
Integration

Phase 2 - FAISS - Multiple device - Dashboard - Monitoring

Phase 3 - Liveness Detection - Anti spoofing - Mobile attendance -
Offline synchronization

------------------------------------------------------------------------

# Status Implementasi Repository (2026-07-08)

Dokumen ini sekarang merefleksikan implementasi aktual pada repository
`fastapi-fd`.

## Struktur Aktual

``` text
fastapi-fd/
├── .gitignore
├── main.py
├── requirements.txt
├── constraints.txt
├── alembic.ini
├── config/
│   ├── database.py
│   └── settings.py
├── models/
│   └── face_attendance.py
├── schemas/
│   ├── common.py
│   ├── face_enrollment.py
│   ├── attendance.py
│   └── device.py
├── services/
│   ├── image_service.py
│   ├── mediapipe_service.py
│   ├── embedding_service.py
│   ├── faiss_service.py
│   ├── attendance_service.py
│   ├── geolocation_service.py
│   ├── odoo_service.py
│   ├── local_storage_service.py
│   ├── object_storage_service.py
│   ├── sample_media_storage_service.py
│   └── camera_service.py
├── routes/
│   ├── face_enrollment.py
│   ├── attendance.py
│   └── device.py
├── supports/
│   ├── json_response.py
│   └── exception_handlers.py
├── migrations/
│   ├── env.py
│   └── versions/
│       ├── 20260708_0001_create_face_attendance_tables.py
│       ├── 20260708_0002_alter_face_sample_image_path_to_text.py
│       ├── 20260708_0003_create_face_sample_storage_table.py
│       └── 20260708_0004_add_gps_fields_to_attendance_attempt.py
├── scripts/
│   └── setup_env.ps1
├── docs/
│   ├── FastAPI_Face_Attendance_Architecture.md
│   ├── Odoo14_Community_Integration_Guide.md
│   ├── Frontend_Vue_Implementation_Guide.md
│   ├── Dependency_Troubleshooting.md
│   └── Dependency_Changelog.md
└── tests/
    ├── conftest.py
    └── test_api_smoke.py
```

## Standar JSON Response

Semua response API bisnis menggunakan envelope baku dari
`supports/json_response.py`:

- success
- code
- message
- data
- errors
- meta
- timestamp_utc

Global exception handler di `supports/exception_handlers.py` memastikan
error 422/HTTPException/500 mengikuti format yang konsisten.

## Catatan Implementasi Penting

- Face image disimpan ke 3 target sekaligus melalui service layer:
    - local filesystem (`uploads/local/...`)
    - object-style storage URL (`uploads/object/...`)
    - Odoo attachment (placeholder service)
- Metadata storage disimpan di tabel `face_sample_storage`.
- Attendance sekarang mendukung penyimpanan GPS (`latitude`, `longitude`,
    `gps_accuracy_meters`, `gps_provider`) pada `face_attendance_attempt`.
- Data GPS ini dimaksudkan untuk dikirim ke Odoo 14 agar validasi radius
    attendance bisa diterapkan di sisi Odoo.
- Geolocation helper tersedia di `services/geolocation_service.py` untuk
    kebutuhan perhitungan jarak/radius di tahap lanjutan.
- Enrollment embedding diambil dari sample valid terbaru, sehingga source
    embedding enrollment dan attendance konsisten.
- Attendance history menyimpan audit trail match success/failed.

## Perintah Operasional

Migrasi:

``` bash
python -m alembic upgrade head
```

Jalankan aplikasi:

``` bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Jalankan test:

``` bash
python -m pytest -q
```

## Dependency Update (2026-07-08)

- Seluruh paket pada `requirements.txt` telah diverifikasi terhadap
    environment aktif.
- `greenlet` berhasil di-upgrade dari `2.0.2` menjadi `3.1.1`.
- Upaya ke `greenlet 3.2.x` gagal di Python 3.9 Windows karena tidak ada
    wheel yang cocok dan membutuhkan Microsoft C++ Build Tools.

Rekomendasi jika ingin pakai greenlet terbaru:

1. Upgrade runtime ke Python 3.10+.
2. Atau install Microsoft C++ Build Tools pada host Windows.

## Dependency Files

Repository ini menggunakan dua file dependency:

- `requirements.txt` untuk dependency utama aplikasi.
- `constraints.txt` untuk snapshot dependency lengkap yang sudah teruji.

Install yang direkomendasikan:

``` bash
python -m pip install -c constraints.txt -r requirements.txt
```

Atau gunakan script otomatis (Windows PowerShell):

``` powershell
./scripts/setup_env.ps1
```

Detail troubleshooting dependency ada di:

- `docs/Dependency_Troubleshooting.md`
- `docs/Dependency_Changelog.md`

Dokumentasi implementasi lanjutan:

- `docs/Odoo14_Community_Integration_Guide.md`
- `docs/Frontend_Vue_Implementation_Guide.md`
