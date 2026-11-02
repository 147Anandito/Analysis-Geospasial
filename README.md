# Web GIS & Dashboard Campak Sumenep - Local Flask

Project lokal skripsi: analisis spasial Moran's I, LISA, dan prediksi time series Random Forest Regression berbasis lag feature.

## Cara Menjalankan

```bash
cd campak_sumenep_local
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Buka browser:

```text
http://127.0.0.1:5000
```

## Struktur

```text
campak_sumenep_local/
├── run.py
├── requirements.txt
├── README.md
└── app/
    ├── __init__.py
    ├── routes.py
    ├── services.py
    ├── templates/index.html
    ├── static/css/style.css
    ├── static/js/app.js
    ├── data/Data Suspek Campak.xlsx
    └── models/
```

## Catatan Penting Skripsi

- File Excel 2025 berisi data detail per kasus, sehingga bisa dipakai untuk agregasi bulanan, kecamatan, jenis kelamin, umur, dan imunisasi.
- Sheet 2022, 2023, dan 2024 berisi rekap kecamatan/puskesmas, sehingga bisa dipakai untuk tren tahunan dan analisis spasial tahunan, tetapi belum cukup kuat untuk forecasting bulanan kecuali tersedia data bulanan.
- Moran's I dan LISA idealnya memakai GeoJSON/shapefile kecamatan Sumenep. Project ini tetap berjalan lokal dengan koordinat fallback, tetapi hasil final skripsi lebih baik memakai GeoJSON kecamatan.

## Endpoint API

- `/api/summary`
- `/api/kecamatan?year=2025`
- `/api/timeseries`
- `/api/spatial?year=2025`
- `/api/forecast?steps=6`
- `/api/upload` POST file Excel/CSV
