from pathlib import Path
from flask import Blueprint, current_app, jsonify, render_template, request
from werkzeug.utils import secure_filename
import joblib
from .services import kecamatan_summary, timeseries, spatial_analysis, forecast, load_project_data

bp = Blueprint("main", __name__)


def data_path() -> Path:
    return Path(current_app.config["DATA_PATH"])


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/summary")
def api_summary():
    ts = timeseries(data_path())
    latest = 2025 if any(x["tahun"] == 2025 for x in ts["annual"]) else max([x["tahun"] for x in ts["annual"]], default=2025)
    kec = kecamatan_summary(data_path(), latest)
    spatial = spatial_analysis(data_path(), latest)
    total = sum(x["jumlah_kasus"] for x in kec)
    return jsonify({
        "latest_year": latest,
        "total_cases": total,
        "total_kecamatan": len(kec),
        "top_kecamatan": kec[:5],
        "moran_i": spatial.get("moran_i"),
        "z_score": spatial.get("z_score"),
        "warning": spatial.get("warning"),
    })


@bp.route("/api/kecamatan")
def api_kecamatan():
    year = int(request.args.get("year", 2025))
    return jsonify(kecamatan_summary(data_path(), year))


@bp.route("/api/timeseries")
def api_timeseries():
    return jsonify(timeseries(data_path()))


@bp.route("/api/spatial")
def api_spatial():
    year = int(request.args.get("year", 2025))
    return jsonify(spatial_analysis(data_path(), year))


@bp.route("/api/forecast")
def api_forecast():
    steps = int(request.args.get("steps", 6))
    return jsonify(forecast(data_path(), steps))


@bp.route("/api/geojson")
def api_geojson():
    import json
    geojson_path = data_path() / "Kabupaten Sumenep-KECAMATAN.geojson"
    if not geojson_path.exists():
        return jsonify({"error": "GeoJSON tidak ditemukan"}), 404
    with open(geojson_path, encoding="utf-8") as f:
        gj = json.load(f)
    # Standardize kecamatan names in properties
    from .analysis.spatial_analysis import standardisasi_kecamatan_spasial
    import pandas as pd
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        name_col = next((k for k in ["Kecamatan", "KECAMATAN", "kecamatan", "nama", "NAME_3", "WADMKC"] if k in props), None)
        if name_col:
            raw = props[name_col]
            std = standardisasi_kecamatan_spasial(pd.Series([raw])).iloc[0]
            props["kecamatan_std"] = std
    return jsonify(gj)


@bp.route("/api/predict")
def api_predict():
    try:
        l1 = float(request.args.get("lag1", 0))
        l2 = float(request.args.get("lag2", 0))
        l3 = float(request.args.get("lag3", 0))
        l4 = float(request.args.get("lag4", 0))
        m = int(request.args.get("month", 1))
        y = int(request.args.get("year", 2026))

        model_path = Path(current_app.root_path) / "models" / "model_random_forest_campak.pkl"
        if not model_path.exists():
            return jsonify({"error": f"Model file not found at {model_path}"}), 500

        model_data = joblib.load(model_path)
        model = model_data["model"]

        # Features: ['Lag_1', 'Lag_2', 'Lag_3', 'Lag_4', 'Bulan', 'Tahun']
        X = [[l1, l2, l3, l4, m, y]]
        pred = model.predict(X)[0]
        pred = max(0.0, float(pred))

        return jsonify({"prediction": round(pred, 3)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "File tidak ditemukan."}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Nama file kosong."}), 400
    filename = secure_filename(f.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in [".xlsx", ".xls"]:
        return jsonify({"error": "Upload saat ini menerima Excel .xlsx/.xls."}), 400
    save_path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    f.save(save_path)
    # Upload dapat dipakai untuk mengganti file utama. Untuk data skripsi lengkap, tetap simpan 2022.xlsx, 2023.xlsx, 2024.xlsx, 2025.xlsx, dan GeoJSON di app/data.
    current_app.config["DATA_PATH"] = save_path.parent
    load_project_data.cache_clear()
    return jsonify({"message": "Dataset berhasil diupload. Untuk analisis lengkap, pastikan semua file tahunan dan GeoJSON tersedia di app/data.", "filename": filename})
