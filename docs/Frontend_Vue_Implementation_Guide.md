# Frontend Vue Implementation Guide

Dokumen ini adalah panduan implementasi frontend Vue.js untuk integrasi dengan FastAPI Face Attendance Service.

## 1. Tujuan Frontend

Frontend bertanggung jawab untuk:

- capture stream kamera
- capture koordinat GPS user/device saat attendance
- melakukan quality gate ringan sebelum upload
- kirim image ke endpoint enrollment/attendance
- menampilkan feedback real-time ke user
- menangani retry dan status error secara jelas

## 2. Stack yang Direkomendasikan

- Vue 3 + Composition API
- Vite
- Pinia (state management)
- Axios atau Fetch wrapper
- OpenCV.js (opsional untuk precheck)

## 3. Struktur Folder Frontend yang Disarankan

```text
src/
├── api/
│   ├── client.ts
│   ├── attendance.ts
│   └── enroll.ts
├── components/
│   ├── camera/
│   │   ├── CameraPreview.vue
│   │   ├── FaceGuideOverlay.vue
│   │   └── QualityIndicator.vue
│   └── common/
├── views/
│   ├── EnrollView.vue
│   ├── AttendanceView.vue
│   └── DeviceSetupView.vue
├── stores/
│   ├── camera.store.ts
│   ├── enroll.store.ts
│   └── attendance.store.ts
├── composables/
│   ├── useCamera.ts
│   ├── useCapture.ts
│   └── useQualityCheck.ts
└── types/
    └── api.ts
```

## 4. Konfigurasi Environment

Contoh `.env` frontend:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_CAPTURE_FORMAT=image/png
VITE_CAPTURE_QUALITY=0.9
VITE_SAMPLE_MIN_COUNT=5
VITE_REQUEST_TIMEOUT_MS=15000
VITE_GEOLOCATION_ENABLE_HIGH_ACCURACY=true
VITE_GEOLOCATION_TIMEOUT_MS=10000
```

Catatan inference:

- Frontend tidak perlu mengetahui detail model ONNX.
- Backend akan mengembalikan `embedding_provider` pada hasil enrollment/attendance.
- Nilai provider dapat berupa `visual` atau `onnx`; gunakan hanya untuk badge/debug/admin UI, bukan untuk logic bisnis frontend.

## 5. Kontrak API yang Digunakan Frontend

Endpoint utama:

- `POST /api/v1/face/enroll/start`
- `POST /api/v1/face/enroll/sample`
- `POST /api/v1/face/enroll/finish`
- `GET /api/v1/face/enroll/{employee_id}`
- `POST /api/v1/attendance/checkin`
- `POST /api/v1/attendance/checkout`
- `GET /api/v1/attendance/history`

Envelope response standar:

```json
{
  "success": true,
  "code": "SAMPLE_SAVED",
  "message": "Sample saved",
  "data": {},
  "errors": null,
  "meta": null,
  "timestamp_utc": "2026-07-08T09:00:00Z"
}
```

## 6. Alur Enrollment di Frontend

1. User memilih employee.
2. Frontend panggil `enroll/start`.
3. Frontend capture beberapa frame (target minimal 5 accepted sample).
4. Tiap frame dikirim ke `enroll/sample`.
5. Frontend baca hasil accepted/rejected dari response.
6. Jika accepted mencukupi, panggil `enroll/finish`.

Data penting dari `enroll/sample` response:

- `data.accepted`
- `data.reason_codes`
- `data.blur_score`
- `data.brightness_score`
- `data.storage.local_url`
- `data.storage.object_url`
- `data.storage.odoo_attachment_id`

Data penting dari `enroll/finish` response:

- `data.employee_id`
- `data.accepted_samples`
- `data.templates_created`
- `data.embedding_provider`
- `data.status`

Catatan penting:

- Upload 5-10 foto karyawan tidak mengubah file model `.onnx`.
- Foto yang diterima backend akan dikonversi menjadi embedding/template dan disimpan di database.
- Jika model `.onnx` diganti atau provider berubah, lakukan enrollment ulang semua employee agar template lama tidak bercampur dengan template provider baru.

## 7. Alur Attendance di Frontend

1. User pilih aksi checkin/checkout.
2. Ambil koordinat GPS via browser geolocation API.
3. Capture satu frame berkualitas baik.
4. Kirim image + koordinat GPS ke endpoint attendance.
5. Tampilkan hasil:
   - matched / not matched
   - employee_id
   - similarity
   - status
  - status lokasi jika dikembalikan sistem Odoo/backend

Rekomendasi flow bisnis frontend:

- jangan izinkan submit attendance jika permission lokasi ditolak
- jangan izinkan submit jika `coords` belum tersedia
- jika akurasi terlalu buruk, tampilkan peringatan dan minta user retry
- kirim metadata GPS apa adanya ke backend, biarkan Odoo menentukan valid/tidak berdasarkan radius

Payload attendance yang direkomendasikan dari frontend:

```json
{
  "device_code": "CAM-001",
  "image_base64": "...",
  "latitude": -6.1753924,
  "longitude": 106.8271528,
  "gps_accuracy_meters": 8.75,
  "gps_provider": "browser"
}
```

Contoh field response attendance yang harus di-handle frontend:

```json
{
  "attempt_id": 3,
  "action": "checkin",
  "matched": true,
  "employee_id": "EMP001",
  "similarity": 0.98,
  "quality_score": 3200.5,
  "embedding_provider": "onnx",
  "odoo_sync_status": "success",
  "odoo_attendance_id": "4567",
  "status": "success",
  "latitude": -6.1753924,
  "longitude": 106.8271528,
  "gps_accuracy_meters": 8.75
}
```

## 8. Implementasi Camera Composable (Konsep)

`useCamera.ts` sebaiknya menyediakan:

- `startCamera(deviceId?)`
- `stopCamera()`
- `captureFrame(): Promise<string>` (base64)
- state `isReady`, `stream`, `error`

Praktik penting:

- set `video.playsInline = true`
- request resolusi moderat (misal 640x480) untuk latency rendah
- cleanup stream pada unmount

## 8.1 Implementasi Geolocation Composable (Konsep)

`useGeolocation.ts` sebaiknya menyediakan:

- `requestLocation()`
- `clearLocation()`
- state `coords`, `accuracy`, `loading`, `error`

Gunakan `navigator.geolocation.getCurrentPosition()` dengan opsi:

- `enableHighAccuracy: true`
- `timeout: 10000`
- `maximumAge: 0`

Fallback UX yang disarankan:

- jika GPS gagal didapat, tampilkan alasan dan blok attendance
- jika akurasi terlalu buruk, minta user ulangi deteksi lokasi
- tampilkan nilai akurasi aktual agar user paham kenapa attendance ditolak

Threshold UX yang disarankan:

- `<= 20m`: sangat baik
- `21m - 50m`: masih bisa dipakai, beri warning ringan
- `> 50m`: minta user ambil ulang lokasi

## 9. Quality Gate di Frontend (Ringan)

Sebelum upload, lakukan precheck:

- brightness tidak terlalu gelap/terang
- blur kasar (optional)
- face area berada di guide overlay

Catatan:

- quality gate final tetap di backend
- frontend precheck hanya untuk UX dan efisiensi bandwidth

## 10. State Management Rekomendasi

`enroll.store.ts`:

- selectedEmployee
- sessionStatus
- samplesAccepted
- samplesRejected
- lastSampleResult

`attendance.store.ts`:

- actionType
- lastResult
- loading
- error
- location
- locationPermission
- locationAccuracy

## 11. Error Handling UX

Kelompokkan error:

- validation error (422): tampilkan pesan actionable
- not found (404): data employee/perangkat tidak ditemukan
- server error (500): tampilkan fallback + tombol retry
- network error: auto-retry terbatas + notifikasi
- geolocation denied: tampilkan instruksi aktivasi permission lokasi
- geolocation timeout: beri opsi retry lokasi

Saran UX:

- tampilkan toast + area detail
- simpan `request_id/event_id` jika ada, agar mudah tracing
- tampilkan badge lokasi: `GPS ready`, `GPS denied`, `Low accuracy`

## 12. Strategi Retry Frontend

Untuk endpoint sample/attendance:

- retry maksimal 2 kali pada timeout/network error
- tanpa retry untuk 4xx validation
- gunakan backoff sederhana (500ms -> 1500ms)

## 13. Keamanan Frontend

- jangan simpan secret di browser
- gunakan token pendek (short-lived) jika auth diaktifkan
- batasi data sensitif di localStorage
- bersihkan frame image dari memory setelah request selesai

## 14. Checklist Implementasi Vue

- halaman enrollment
- halaman attendance
- device selector kamera
- permission request untuk kamera dan lokasi
- indikator kualitas real-time
- indikator kualitas GPS / akurasi lokasi
- progress accepted samples
- hasil attendance + reason jika gagal
- log/history viewer sederhana

## 15. Contoh TypeScript Interface

```ts
export interface ApiEnvelope<T> {
  success: boolean
  code: string
  message: string
  data: T
  errors: unknown
  meta: Record<string, unknown> | null
  timestamp_utc: string
}

export interface EnrollmentSampleData {
  sample_id: number
  accepted: boolean
  reason_codes: string[]
  blur_score: number
  brightness_score: number
  face_count: number
  detector_confidence: number
  storage: {
    local_path: string
    local_url: string
    object_url: string
    odoo_attachment_id: string | null
  }
}

export interface EnrollmentFinishData {
  employee_id: string
  accepted_samples: number
  templates_created: number
  embedding_provider: 'visual' | 'onnx'
  status: string
}

export interface AttendanceRequestPayload {
  device_code?: string
  image_base64: string
  latitude?: number
  longitude?: number
  gps_accuracy_meters?: number
  gps_provider?: string
}

export interface AttendanceResultData {
  attempt_id: number
  action: 'checkin' | 'checkout'
  matched: boolean
  employee_id: string | null
  similarity: number
  quality_score: number
  embedding_provider: 'visual' | 'onnx'
  odoo_sync_status: string | null
  odoo_attendance_id: string | null
  status: string
  latitude: number | null
  longitude: number | null
  gps_accuracy_meters: number | null
  gps_provider?: string | null
}
```

## 16. Testing Frontend yang Disarankan

Unit test:

- composable camera lifecycle
- API client parse envelope
- store transition state

E2E test:

- enrollment happy path
- enrollment insufficient sample
- attendance match success
- attendance not matched
- attendance gagal karena GPS permission denied
- attendance gagal karena lokasi di luar radius

## 17. Integrasi dengan Odoo UI (Opsional)

Jika frontend ini di-embed atau terhubung ke Odoo:

- kirim `employee_id` dari context Odoo ke view Vue
- gunakan deep-link kembali ke form attendance Odoo setelah success
- tampilkan link evidence image jika disediakan backend

## 18. Catatan Praktis untuk Repo Ini

Backend saat ini sudah mengembalikan metadata storage pada endpoint
`enroll/sample`.

Backend attendance juga sudah menerima dan mengembalikan field GPS:

- `latitude`
- `longitude`
- `gps_accuracy_meters`
- `gps_provider`

Frontend cukup memanfaatkan field tersebut untuk:

- preview quick link image (`local_url` / `object_url`)
- menampilkan status attachment Odoo (`odoo_attachment_id`)
- menampilkan bukti koordinat yang dikirim saat attendance
- menyiapkan UX untuk hasil validasi radius dari Odoo pada tahap integrasi berikutnya

## 19. Status Implementasi Backend Saat Ini

Hal yang sudah tersedia di backend:

- endpoint attendance menerima `latitude`, `longitude`, `gps_accuracy_meters`, `gps_provider`
- response attendance mengembalikan field GPS tersebut
- response attendance mengembalikan `embedding_provider`
- response attendance mengembalikan status sinkronisasi Odoo (`odoo_sync_status`, `odoo_attendance_id`) jika match berhasil
- history attendance juga mengembalikan data GPS
- endpoint sample enrollment mengembalikan metadata storage image
- endpoint sample enrollment mengembalikan `reason_codes` untuk sample yang ditolak
- endpoint finish enrollment membuat multi-template dari semua sample valid, bukan hanya satu foto

Implikasi untuk frontend:

- frontend tidak perlu menghitung radius sendiri
- frontend cukup mengambil GPS terbaik yang tersedia dari browser/device
- frontend perlu menampilkan hasil validasi lokasi jika nanti dikembalikan Odoo
- frontend perlu menangani permission kamera dan lokasi sebagai syarat utama attendance

Roadmap migrasi inferensi backend yang menjadi acuan frontend ada di:

- `docs/Inference_Pipeline_Roadmap.md`
