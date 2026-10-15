# Dependency Troubleshooting

Dokumen ini berisi panduan cepat saat instalasi dependency pada proyek
`fastapi-fd`.

## Versi Python

Environment aktif saat verifikasi:

- Python 3.9.13
- OS: Windows

Jika menggunakan versi Python berbeda, beberapa paket (khususnya paket
berbasis C-extension) dapat menghasilkan versi resolusi yang berbeda.

## Cara Install Stabil (Direkomendasikan)

1. Install top-level dependency:

```bash
python -m pip install -r requirements.txt
```

2. Pastikan transitive dependency konsisten:

```bash
python -m pip install -c constraints.txt -r requirements.txt
```

`requirements.txt` berisi dependency utama proyek.
`constraints.txt` berisi snapshot lengkap environment terverifikasi.

## Kasus greenlet di Windows + Python 3.9

Masalah yang ditemukan:

- Versi `greenlet 3.2.x` tidak menyediakan wheel yang cocok untuk setup
  ini.
- Pip mencoba build dari source dan gagal jika Microsoft C++ Build Tools
  belum terpasang.

Status saat ini:

- `greenlet==3.1.1` digunakan dan stabil pada environment ini.

Jika ingin upgrade greenlet lebih jauh:

1. Upgrade ke Python 3.10 atau lebih baru.
2. Atau install Microsoft C++ Build Tools.

## Refresh Dependency Snapshot

Setelah upgrade paket yang berhasil diverifikasi:

```bash
python -m pip freeze > constraints.txt
python -m pytest -q
```

Commit update `requirements.txt` dan `constraints.txt` bersamaan agar
riwayat dependency tetap konsisten.

## Catatan Storage Foto

Implementasi terbaru menyimpan foto enrollment ke tiga target sekaligus:

- local filesystem
- object-style storage URL
- Odoo attachment placeholder

Metadata disimpan di tabel `face_sample_storage` (migrasi
`20260708_0003_create_face_sample_storage_table.py`).
# Enrollment gagal dengan `INVALID_FACE_COUNT` dan `LOW_DETECTION_CONFIDENCE`

Jika `face_count=0` untuk semua foto meskipun sample secara visual berisi satu
wajah, periksa versi MediaPipe. MediaPipe `0.10.35` tidak menyediakan lagi API
legacy `mp.solutions` yang dipakai adapter lama. Production menggunakan OpenCV
Haar Cascade sebagai fallback detector CPU yang tervalidasi pada sample pilot.

Periksa:

```bash
curl -fsS https://hris.kanjabung.web.id/health
grep '^FACE_DETECTOR_PROVIDER=' /var/www/fastapi_app/.env
```

Nilai production yang digunakan adalah `FACE_DETECTOR_PROVIDER=opencv`.

## Wajah benar tetapi selalu tidak dikenal

Pastikan enrollment dan presensi memakai preprocessing embedding yang sama.
Production memotong wajah terbesar dengan OpenCV sebelum embedding ONNX dibuat.
Setelah mengubah preprocessing, template lama tidak boleh langsung dipakai;
regenerasi template dari sample accepted dan rebuild face index menggunakan
runbook deployment. Verifikasi `GET /health` bahwa `embedding_provider` adalah
`onnx` dan jumlah `face_index.entries` sesuai template aktif.

Jangan menurunkan `FACE_RECOGNITION_THRESHOLD` tanpa menguji false-positive.
Threshold adalah kontrol keamanan presensi; kalibrasi harus menggunakan sample
genuine dan impostor yang memadai.
Pastikan wajah memenuhi area panduan, hanya satu wajah terlihat, dan gambar
tidak tertutup objek. Setelah perubahan detector, restart service dan ulangi
sample; enrollment lama yang masih `in_progress` dapat dilanjutkan.

# Enrollment gagal dengan `INVALID_FACE_COUNT` dan `LOW_DETECTION_CONFIDENCE`

Jika `face_count=0` untuk semua foto meskipun sample secara visual berisi satu
wajah, periksa versi MediaPipe. MediaPipe `0.10.35` tidak menyediakan lagi API
legacy `mp.solutions` yang dipakai adapter lama. Production menggunakan OpenCV
Haar Cascade sebagai fallback detector CPU yang tervalidasi pada sample pilot.

Periksa:

```bash
curl -fsS https://hris.kanjabung.web.id/health
grep '^FACE_DETECTOR_PROVIDER=' /var/www/fastapi_app/.env
```

Nilai production yang digunakan adalah `FACE_DETECTOR_PROVIDER=opencv`.
Pastikan wajah memenuhi area panduan, hanya satu wajah terlihat, dan gambar
tidak tertutup objek. Setelah perubahan detector, restart service dan ulangi
sample; enrollment lama yang masih `in_progress` dapat dilanjutkan.

