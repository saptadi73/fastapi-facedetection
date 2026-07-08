# Frontend Vue Implementation Guide

Dokumen ini adalah panduan implementasi frontend Vue.js untuk integrasi dengan FastAPI Face Attendance Service.

## 1. Tujuan Frontend

Frontend bertanggung jawab untuk:

- capture stream kamera
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
```

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
- `data.blur_score`
- `data.brightness_score`
- `data.storage.local_url`
- `data.storage.object_url`
- `data.storage.odoo_attachment_id`

## 7. Alur Attendance di Frontend

1. User pilih aksi checkin/checkout.
2. Capture satu frame berkualitas baik.
3. Kirim ke endpoint attendance.
4. Tampilkan hasil:
   - matched / not matched
   - employee_id
   - similarity
   - status

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

## 11. Error Handling UX

Kelompokkan error:

- validation error (422): tampilkan pesan actionable
- not found (404): data employee/perangkat tidak ditemukan
- server error (500): tampilkan fallback + tombol retry
- network error: auto-retry terbatas + notifikasi

Saran UX:

- tampilkan toast + area detail
- simpan `request_id/event_id` jika ada, agar mudah tracing

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
- indikator kualitas real-time
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

## 17. Integrasi dengan Odoo UI (Opsional)

Jika frontend ini di-embed atau terhubung ke Odoo:

- kirim `employee_id` dari context Odoo ke view Vue
- gunakan deep-link kembali ke form attendance Odoo setelah success
- tampilkan link evidence image jika disediakan backend

## 18. Catatan Praktis untuk Repo Ini

Backend saat ini sudah mengembalikan metadata storage pada endpoint
`enroll/sample`.

Frontend cukup memanfaatkan field tersebut untuk:

- preview quick link image (`local_url` / `object_url`)
- menampilkan status attachment Odoo (`odoo_attachment_id`)
