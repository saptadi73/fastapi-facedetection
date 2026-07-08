# Inference Pipeline Roadmap

Dokumen ini menjelaskan roadmap migrasi dari implementasi placeholder saat ini ke pipeline inferensi wajah production-grade berbasis MediaPipe + embedding model + FAISS.

## 1. Tujuan Roadmap

Tujuan utama:

- meningkatkan akurasi match wajah di kondisi lapangan
- menjaga latency tetap rendah saat jumlah employee bertambah
- menyediakan kontrol kualitas biometric yang terukur
- memastikan integrasi attendance ke Odoo tetap stabil

## 2. Kondisi Saat Ini

Status backend saat ini:

- deteksi wajah masih placeholder logic
- pencarian kandidat masih in-memory nearest neighbor sederhana
- quality check masih basic
- alur API enrollment/attendance, storage, GPS, dan integrasi Odoo sudah berjalan

Artinya, fondasi arsitektur sudah ada, tetapi engine inferensi real belum aktif.

## 3. KPI Target Production

KPI yang direkomendasikan:

- false accept rate (FAR) <= 0.1%
- false reject rate (FRR) <= 1.5%
- p95 latency inference <= 800 ms (single face)
- p95 end-to-end attendance <= 1500 ms
- success sync ke Odoo >= 99.5%

## 4. Milestone dan Fase Implementasi

## Fase 0 - Baseline dan Instrumentasi (1-2 minggu)

Deliverable:

- logging metrik kualitas dan similarity per attempt
- dashboard baseline latency dan mismatch
- dataset evaluasi awal (internal pilot)

Tugas teknis:

- tambahkan telemetry per endpoint attendance
- simpan reason code untuk gagal match
- tetapkan threshold awal berbasis data riil

Exit criteria:

- baseline metrik tersedia minimal 1 minggu data nyata
- top 3 penyebab mismatch teridentifikasi

## Fase 1 - MediaPipe Real Detection (2-3 minggu)

Deliverable:

- aktivasi deteksi wajah dan landmark MediaPipe nyata
- validasi quality gate (single face, confidence, pose)
- tuning threshold quality untuk enrollment dan attendance

Tugas teknis:

- ganti placeholder di service deteksi dengan MediaPipe real
- tambahkan filtering pose (yaw/pitch/roll) dan confidence
- update response dengan reason code validasi yang jelas

Exit criteria:

- deteksi wajah stabil di lingkungan pilot
- quality gate menurunkan sample buruk tanpa menurunkan UX drastis

## Fase 2 - Embedding Model Production (2-3 minggu)

Deliverable:

- pipeline embedding real (CPU optimized)
- normalisasi embedding konsisten di enrollment dan attendance
- evaluasi threshold similarity berbasis data pilot

Tugas teknis:

- pilih model embedding yang sesuai SLA (CPU/GPU)
- buat benchmark akurasi per kondisi cahaya/pose
- kalibrasi threshold per environment jika perlu

Exit criteria:

- FAR/FRR membaik signifikan dari baseline
- hasil benchmark terdokumentasi dan repeatable

## Fase 3 - FAISS Native Index (2-3 minggu)

Deliverable:

- index FAISS real (Flat/HNSW/IVF sesuai skala)
- proses rebuild/refresh index terotomasi
- fallback jika index unavailable

Tugas teknis:

- implement add/update/remove embedding ke FAISS index
- tetapkan strategi persist index dan warmup startup
- benchmark latency terhadap jumlah template

Exit criteria:

- p95 latency search stabil pada beban target
- operasi update template tidak menyebabkan downtime layanan

## Fase 4 - Hardening Production + Odoo Radius Enforcement (2 minggu)

Deliverable:

- retry dan reprocess queue sinkronisasi Odoo
- validasi radius attendance aktif di Odoo custom module
- monitoring + alerting operasional

Tugas teknis:

- idempotency event attendance end-to-end
- observability (log, metric, alert)
- runbook incident dan recovery index

Exit criteria:

- SLO latency dan reliability tercapai
- UAT lintas site lulus

## 5. Strategi Deploy dan Rollout

Strategi rollout yang disarankan:

1. shadow mode: model baru hitung hasil tapi tidak memengaruhi keputusan final
2. canary site: aktifkan di 1 lokasi pilot
3. staged rollout: tambah site bertahap berdasarkan metrik
4. full rollout: aktifkan global setelah KPI stabil

## 6. Rekomendasi Infrastruktur

### Review Kebutuhan AVX untuk Go-Live Saat Ini

Berdasarkan implementasi dan dependency yang ada saat ini, aplikasi belum wajib memakai server CPU AVX/AVX2 untuk bisa live.

Alasannya:

- `requirements.txt` belum memakai library inferensi native seperti MediaPipe, FAISS, OpenCV, ONNX Runtime, TensorFlow, PyTorch, atau NumPy.
- `services/mediapipe_service.py` masih placeholder berbasis ukuran gambar, bukan MediaPipe native.
- `services/embedding_service.py` masih memakai `hashlib` dan operasi list Python untuk menghasilkan embedding deterministik, bukan model neural network.
- `services/faiss_service.py` masih in-memory nearest-neighbor sederhana, bukan FAISS native index.
- quality check gambar masih memakai Pillow (`pillow`), yang tidak menetapkan AVX sebagai syarat deploy aplikasi.

Kesimpulan operasional:

- Untuk go-live terbatas dengan pipeline placeholder saat ini, server non-AVX masih bisa digunakan selama Python dan dependency yang dipakai berhasil terinstal.
- Risiko utamanya bukan kompatibilitas AVX, melainkan akurasi biometrik: hasil face detection, embedding, dan matching saat ini belum layak dianggap sebagai verifikasi wajah production-grade.
- Jika aplikasi dipakai untuk attendance riil sebelum Fase 1-3 selesai, sebaiknya diposisikan sebagai pilot/internal UAT atau digabung dengan kontrol tambahan seperti validasi device, GPS, approval HR, atau audit log.

Kapan AVX mulai perlu dipertimbangkan:

- saat Fase 1 mengaktifkan MediaPipe real detection
- saat Fase 2 memakai embedding model native/optimized
- saat Fase 3 mengganti pencarian in-memory menjadi FAISS native
- saat target latency dan concurrency mulai ketat

Pada fase tersebut, beberapa wheel/library native dapat membutuhkan instruksi CPU tertentu atau jauh lebih stabil/cepat di CPU modern. Karena itu, sebelum upgrade pipeline inferensi, lakukan benchmark dan install test di tipe server target.

Minimum yang direkomendasikan untuk production inference CPU setelah pipeline real aktif:

- CPU modern dengan AVX2 + FMA (disarankan)
- RAM minimal 8-16 GB (tergantung ukuran template/index)
- storage SSD

Catatan keputusan:

- Status sekarang: AVX/AVX2 belum menjadi syarat wajib aplikasi.
- Status setelah real inference aktif: AVX2 + FMA direkomendasikan kuat sebagai baseline server production.
- Keputusan final hardware harus mengikuti hasil benchmark model dan library yang benar-benar dipilih pada Fase 1-3.

Saat volume tinggi:

- pertimbangkan worker inference terpisah
- gunakan queue untuk task non-critical
- siapkan horizontal scaling API node

## 7. Risk Register Ringkas

Risiko utama:

- kualitas kamera/device tidak konsisten
- perubahan pencahayaan ekstrem menyebabkan FRR naik
- drift threshold saat user base bertambah
- bottleneck sinkronisasi ke Odoo

Mitigasi:

- quality gate ketat + feedback UX
- evaluasi threshold berkala
- monitoring metrik per site/device
- retry queue + reconciler terjadwal

## 8. Rencana Validasi

Validasi teknis:

- unit + integration test pipeline inferensi
- benchmark latency per skenario volume
- load test concurrency attendance

Validasi bisnis:

- UAT HR untuk acceptance attendance
- audit sample mismatch oleh tim operasional
- verifikasi akurasi radius lokasi di Odoo

## 9. Definition of Done per Fase

Sebuah fase dianggap selesai jika:

- fitur utama fase sudah aktif
- metrik target fase tercapai
- dokumentasi operasional diperbarui
- rollback plan tervalidasi

## 10. Artefak Dokumentasi yang Harus Dijaga

Dokumen yang harus selalu sinkron:

- `docs/FastAPI_Face_Attendance_Architecture.md`
- `docs/Odoo14_Community_Integration_Guide.md`
- `docs/Frontend_Vue_Implementation_Guide.md`
- `docs/Inference_Pipeline_Roadmap.md`

## 11. Next Action yang Bisa Langsung Dieksekusi

1. aktifkan Fase 0 (instrumentasi baseline)
2. pilih kandidat model embedding untuk benchmark
3. tentukan target volume employee 6-12 bulan
4. finalkan SLO bersama stakeholder HR dan IT
