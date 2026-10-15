# Kebijakan Group, Home Point, GeoFence, dan Kunjungan

## Tujuan

Presensi dibagi berdasarkan kebijakan group karyawan, bukan satu radius global.

| Kebijakan group | Presensi kantor | Kunjungan pelanggan/mitra |
|---|---|---|
| `office` | Wajib berada di Home Point group | Ditolak |
| `hybrid` | Wajib berada di Home Point group | Diizinkan dengan nama dan catatan |
| `offsite_allowed` | Wajib berada di Home Point group | Diizinkan dengan nama dan catatan |

## Konfigurasi Odoo

1. Buat Home Point pada menu Face Attendance > Locations.
2. Isi nama, kode, latitude, longitude, radius, toleransi akurasi GPS, dan jenis aktivitas.
3. Buat group pada menu Face Attendance > Attendance Groups.
4. Pilih perusahaan, kebijakan group, dan satu atau lebih Home Point.
5. Atur Face Attendance Group pada form employee.
6. Pastikan group memiliki minimal satu Home Point aktif.

Lokasi langsung pada employee dapat menjadi pengecualian khusus. Jika tidak ada
lokasi langsung, sistem menggunakan Home Point group. Employee yang sudah
memiliki group tidak memakai fallback seluruh lokasi perusahaan.

## Alur presensi

Frontend mengirim `attendance_context`:

- `office`: Odoo menghitung jarak GPS ke Home Point group dan memeriksa akurasi serta radius.
- `customer_visit`: Odoo tidak menerapkan radius kantor, tetapi tetap meminta GPS,
  `visit_partner`, dan `visit_note`. Kebijakan group harus `hybrid` atau
  `offsite_allowed`.

Odoo adalah pengambil keputusan terakhir. Frontend hanya membantu kelengkapan input.

## Audit dan UAT

Event menyimpan konteks, pihak yang dikunjungi, catatan, koordinat, akurasi,
jarak, Home Point, status, dan pesan penolakan. Uji minimal: office dalam dan
luar radius, office memilih kunjungan, kunjungan tanpa data wajib, serta
kunjungan group hybrid/offsite dengan data lengkap.
