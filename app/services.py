from __future__ import annotations
from pathlib import Path
from functools import lru_cache

from .analysis.preprocessing import load_all_data, kecamatan_summary as prep_kecamatan_summary 
from .analysis.spatial_analysis import build_spatial
from .analysis.random_forest import train_forecast
from .analysis.time_series import timeseries_data


def _data_dir_from_path(path: Path) -> Path:
    path = Path(path)
    return path if path.is_dir() else path.parent


@lru_cache(maxsize=4)
def load_project_data(path_key: str) -> dict:
    return load_all_data(Path(path_key))


def get_current_data(path: Path) -> dict:
    data_dir = _data_dir_from_path(path)
    return load_project_data(str(data_dir.resolve()))


# Kompatibel dengan routes.py lama
def load_workbook_data(path: str) -> dict:
    return get_current_data(Path(path))


def kecamatan_summary(path: Path, year: int = 2025) -> list[dict]:
    data_dir = _data_dir_from_path(path)
    data = get_current_data(data_dir)
    df = prep_kecamatan_summary(data, year)
    sp = build_spatial(df, data_dir)
    return sp.get("clusters", [])


def timeseries(path: Path) -> dict:
    data = get_current_data(path)
    return timeseries_data(data)


def spatial_analysis(path: Path, year: int = 2025) -> dict:
    data_dir = _data_dir_from_path(path)
    data = get_current_data(data_dir)
    df = prep_kecamatan_summary(data, year)
    return build_spatial(df, data_dir)


def forecast(path: Path, steps: int = 6) -> dict:
    data_dir = _data_dir_from_path(path)
    data = get_current_data(data_dir)
    return train_forecast(data["master_panel"], steps=steps)
