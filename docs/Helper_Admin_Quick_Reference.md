# Helper Admin HR dan Support

## Employee tidak bisa presensi kantor

1. Pastikan employee aktif dan memiliki Face Attendance Group.
2. Pastikan group aktif, perusahaan sesuai, dan memiliki Home Point aktif.
3. Periksa koordinat, radius, dan toleransi akurasi Home Point.
4. Minta pengguna mengambil lokasi ulang di area terbuka.

## Sales presensi saat visit

Pilih **Kunjungan**, isi nama pelanggan/mitra dan catatan tujuan. Employee
harus berada pada group `hybrid` atau `offsite_allowed`; group `office` akan ditolak.

## Kamera di HP

- Gunakan HTTPS.
- Izinkan kamera dan lokasi pada permission situs.
- Tutup aplikasi lain yang memakai kamera.
- Reset permission situs bila sebelumnya memilih “Jangan izinkan”.

## Pemeriksaan service

```bash
systemctl status api-facedetection --no-pager
journalctl -u api-facedetection -n 100 --no-pager
curl -fsS https://hris.kanjabung.web.id/health
```

Jangan menyalin secret API, password, atau token ke tiket support.
