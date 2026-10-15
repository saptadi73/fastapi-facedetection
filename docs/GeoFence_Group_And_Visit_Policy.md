# Kebijakan Group, Home Point, GeoFence, dan Kunjungan

## Tujuan

Presensi dibagi berdasarkan kebijakan group karyawan, bukan satu radius global.

| Kebijakan group | Presensi kantor | Kunjungan pelanggan/mitra |
|---|---|---|
| `office` | Wajib berada di Home Point group | Ditolak |
| `hybrid` | Wajib berada di Home Point group | Diizinkan dengan nama dan catatan |
| `offsite_allowed` | Wajib berada di Home Point group | Diizinkan dengan nama dan catatan |

## Konfigurasi Odoo terbaru

1. Buka **Attendances > Home Points**.
2. Klik **Create** dan isi nama, kode, policy, latitude, longitude, radius,
   toleransi akurasi GPS, jenis aktivitas, dan karyawan.
3. Pada form employee, pilih satu **Home Point**. Policy dan geofence employee
   otomatis mengikuti Home Point tersebut.
4. Menu **Attendance Groups** dan field lokasi langsung dipertahankan sebagai
   legacy/migrasi, tetapi tidak digunakan untuk konfigurasi baru.

Model utama sekarang adalah `Employee -> Home Point`. Home Point menyimpan
koordinat, radius, tipe check-in/check-out, policy office/hybrid/field, dan
daftar employee. Data group lama tetap dibaca sebagai fallback agar upgrade
tidak memutus konfigurasi sebelumnya.

## Alur presensi

Frontend mengirim `attendance_context`:

- `office`: Odoo menghitung jarak GPS ke Home Point employee dan memeriksa akurasi serta radius.
- `customer_visit`: Odoo tidak menerapkan radius kantor, tetapi tetap meminta GPS,
  `visit_partner`, dan `visit_note`. Kebijakan group harus `hybrid` atau
  `offsite_allowed`.

Odoo adalah pengambil keputusan terakhir. Frontend tidak perlu mengetahui
koordinat atau menghitung radius; frontend hanya mengirim konteks `office` atau
`customer_visit`, GPS, dan data kunjungan.

## Audit dan UAT

Event menyimpan konteks, pihak yang dikunjungi, catatan, koordinat, akurasi,
jarak, Home Point, status, dan pesan penolakan. Uji minimal: office dalam dan
luar radius, office memilih kunjungan, kunjungan tanpa data wajib, serta
kunjungan group hybrid/offsite dengan data lengkap.
