from flask import Flask
from flask_cors import CORS
from pathlib import Path

def create_app():
    app = Flask(__name__)
    CORS(app)
    base_dir = Path(__file__).resolve().parent
    app.config["DATA_PATH"] = base_dir / "data"   # sekarang memakai folder app/data berisi 2022, 2023, 2024, 2025, GeoJSON
    app.config["UPLOAD_FOLDER"] = base_dir / "uploads"
    app.config["UPLOAD_FOLDER"].mkdir(exist_ok=True)

    from .routes import bp
    app.register_blueprint(bp)
    return app
