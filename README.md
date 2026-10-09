# Capstone 21 Teknik Geomatika 2023 (WebGIS Desa Sidodadi)

Peta kesesuaian lahan dan aksesibilitas pengepul (Leaflet, tanpa server).

- Jalankan lokal: buka folder di VS Code, klik kanan `index.html`, Open with Live Server.
- Deploy: push ke GitHub, lalu Settings, Pages, Deploy from branch, main / root.
- Ulang pengolahan data: `python processing/convert.py <folder_WEBGIS> data` lalu `python processing/network.py <folder_WEBGIS> data`.
  Parameter network analysis (jumlah pengepul baru, batas kelas, kriteria lokasi) ada di bagian atas `processing/network.py`.

## Struktur
- Layar pembuka, lalu dua peta: **Kesesuaian Lahan** dan **Aksesibilitas Pengepul** (dengan tombol animasi proses penentuan).
- Layer elevasi ditampilkan di peta kesesuaian, tetapi tidak dipakai untuk informasi popup.

## Catatan pembaruan data (Okt 2026)
- Sumber kesesuaian lahan kini `KESESUAIAN LAHAN PERTANIAN2.tif` (kode raster: 5 = S1, 4 = S2, 3 = N, 127 = nodata). `convert.py` dan `network.py` memetakannya ke kode internal 1 = S1, 2 = S2, 3 = N.
- File TIF tidak disertakan di repo (tidak dipakai `index.html`); simpan sumbernya di folder WEBGIS terpisah.
- Titik kebun kini 25 titik dari `Jenis_Kebun.xlsx` (kolom Jenis Kebun, Komoditas, koordinat UTM 48S) beserta foto dokumentasi. Foto disimpan di `data/foto/kebun-NN.jpg` (NN = nomor kebun) dan tampil di popup titik kebun. Ekstrak ulang foto: `python processing/ekstrak_foto.py Jenis_Kebun.xlsx data`.
- `network.py` kini membaca `kebun.json` (Esri JSON dari Excel yang sama), bukan `Ladang.json`. Jarak, kelas aksesibilitas, jalur, lokasi pengepul usulan, dan `proses.json` sudah dihitung ulang untuk 25 titik.
