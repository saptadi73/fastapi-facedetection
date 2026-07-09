# ONNX Face Embedding Setup

Dokumen ini menjelaskan cara mengaktifkan embedding wajah berbasis ONNX Runtime.
Mode default aplikasi tetap `visual` agar development lokal tetap ringan.

## 1. Mode Provider

Provider tersedia:

- `visual`: fallback berbasis fitur gambar dari Pillow
- `auto`: memakai ONNX jika model tersedia, fallback ke `visual`
- `onnx`: wajib memakai ONNX; request akan gagal jika model/dependency tidak siap

## 2. Setup Otomatis

Jalankan script berikut dari root project:

```powershell
.\.venv\Scripts\python.exe scripts\setup_face_model.py
```

Script akan:

- download model pack `buffalo_l.zip` dari release InsightFace v0.7
- mengambil recognition model `w600k_r50.onnx`
- menyimpan hasilnya sebagai `models/face_embedding.onnx`
- memvalidasi model dengan ONNX Runtime CPU provider

Jika zip sudah di-download manual:

```powershell
.\.venv\Scripts\python.exe scripts\setup_face_model.py --zip models\downloads\buffalo_l.zip
```

Contoh `.env`:

```env
FACE_EMBEDDING_PROVIDER=onnx
FACE_ONNX_MODEL_PATH=models/face_embedding.onnx
FACE_ONNX_INPUT_SIZE=112
FACE_ONNX_EXECUTION_PROVIDERS=CPUExecutionProvider
FACE_RECOGNITION_THRESHOLD=0.82
```

## 3. Model

Gunakan model face embedding ONNX yang menghasilkan vector identitas wajah, misalnya
keluarga ArcFace/InsightFace. Simpan file model di folder lokal yang tidak berisi
credential, misalnya:

```text
models/face_embedding.onnx
```

Pipeline preprocessing saat ini:

- input RGB
- resize/crop tengah ke `FACE_ONNX_INPUT_SIZE`
- normalisasi `(pixel - 127.5) / 128.0`
- format tensor `NCHW`
- output pertama diratakan dan dinormalisasi L2

Jika model yang dipilih membutuhkan preprocessing berbeda, sesuaikan
`services/embedding_service.py`.

Hal yang tidak dilakukan otomatis:

- Upload 5-10 foto employee tidak mengubah file `.onnx`.
- Enrollment hanya membuat embedding/template baru di tabel `face_template`.
- Model `.onnx` hanya berubah jika file model diganti manual atau melalui proses training/fine-tuning terpisah.
- Setelah file `.onnx` diganti, semua employee harus enrollment ulang.

Lisensi:

- Model InsightFace pretrained perlu dicek lisensinya sebelum production/komersial.
- Untuk production komersial, gunakan model/lisensi yang memperbolehkan commercial use.

## 4. Server

Untuk production CPU inference disarankan:

- CPU AVX2 + FMA
- RAM 8-16 GB atau lebih sesuai jumlah template
- storage SSD

Setelah model diganti, lakukan enrollment ulang agar template lama tidak bercampur
dengan embedding dari provider berbeda.
