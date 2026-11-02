from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from libpysal.weights import KNN
from libpysal.weights.spatial_lag import lag_spatial
from esda.moran import Moran, Moran_Local

def standardisasi_kecamatan_spasial(series: pd.Series) -> pd.Series:
    mapping = {
        "AMBUTEN": "AMBUNTEN",
        "ARJASA PULAU KANGEAN": "ARJASA",
        "ARJASA (PULAU KANGEAN)": "ARJASA",
        "BATANG-BATANG": "BATANG BATANG",
        "BATANGBATANG": "BATANG BATANG",
        "BATU PUTIH": "BATUPUTIH",
        "GILI GENTENG": "GILIGENTING",
        "GILI GENTING": "GILIGENTING",
        "GILIGENTENG": "GILIGENTING",
        "GILI-GENTENG": "GILIGENTING",
        "GILI-GENTING": "GILIGENTING",
        "GILIGINTING": "GILIGENTING",
        "GULUK-GULUK": "GULUK GULUK",
        "GULUKGULUK": "GULUK GULUK",
        "KECAMATAN KOTA SUMENEP": "KOTA SUMENEP",
        "SUMENEP": "KOTA SUMENEP",
        "NONG GUNONG": "NONGGUNONG",
        "NONG-GUNONG": "NONGGUNONG",
        "RA'AS": "RAAS"
    }
    hasil = (
        series.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"^KEC(?:AMATAN)?\.?\s+", "", regex=True)
        .str.replace(r"[()]", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return hasil.map(lambda x: mapping.get(x, x))

def build_spatial(kecamatan_df: pd.DataFrame, data_dir: Path, k: int = 5, permutations: int = 999) -> dict:
    df = kecamatan_df.copy()
    
    # 1. Load GeoJSON
    geojson_path = None
    for p in [Path(data_dir) / "Kabupaten Sumenep-KECAMATAN.geojson", Path(data_dir) / "batas_kecamatan_sumenep.geojson"]:
        if p.exists():
            geojson_path = p
            break
            
    if not geojson_path:
        return {
            "moran_i": None, "expected_i": None, "z_score": None, "p_value": None,
            "clusters": [], "scatter": [], "warning": "File GeoJSON tidak ditemukan di folder data."
        }
        
    gdf_sumenep = gpd.read_file(geojson_path)
    
    # Standardize names in GeoJSON
    kandidat_kolom = ["Kecamatan", "KECAMATAN", "kecamatan", "nama", "NAME_3", "WADMKC"]
    kolom_kecamatan_peta = next((kolom for kolom in kandidat_kolom if kolom in gdf_sumenep.columns), None)
    if kolom_kecamatan_peta is None:
        kolom_kecamatan_peta = [c for c in gdf_sumenep.columns if c != "geometry" and gdf_sumenep[c].dtype == "object"][0]
        
    gdf_sumenep["Kecamatan_Clean"] = standardisasi_kecamatan_spasial(gdf_sumenep[kolom_kecamatan_peta])
    gdf_sumenep = gdf_sumenep[["Kecamatan_Clean", "geometry"]].dissolve(by="Kecamatan_Clean", as_index=False).reset_index(drop=True)
    
    if not gdf_sumenep.geometry.is_valid.all():
        gdf_sumenep["geometry"] = gdf_sumenep.geometry.buffer(0)
        
    # Standardize names in cases DataFrame to match GeoJSON (GILIGENTING, GULUK GULUK, etc.)
    df["kecamatan_std"] = standardisasi_kecamatan_spasial(df["kecamatan"])
    
    # Merge
    gdf_spasial = gdf_sumenep.merge(
        df, left_on="Kecamatan_Clean", right_on="kecamatan_std", how="left"
    )
    gdf_spasial["jumlah_kasus"] = gdf_spasial["jumlah_kasus"].fillna(0).astype(float)
    
    # Get centroids in EPSG:4326 for Leaflet positioning
    centroids_wgs84 = gdf_spasial.to_crs(epsg=4326).geometry.centroid
    gdf_spasial["lat"] = centroids_wgs84.y
    gdf_spasial["lng"] = centroids_wgs84.x
    
    nilai_spasial = gdf_spasial["jumlah_kasus"].to_numpy(dtype=float)
    
    # Check variance
    if len(nilai_spasial) < 5 or np.isclose(np.var(nilai_spasial), 0):
        # Fallback return
        clusters = []
        for idx, r in gdf_spasial.iterrows():
            clusters.append({
                "kecamatan": r["Kecamatan_Clean"],
                "jumlah_kasus": int(r["jumlah_kasus"]),
                "lat": float(r["lat"]),
                "lng": float(r["lng"]),
                "spatial_lag": 0.0,
                "lisa_cluster": "NS",
                "z_score_local": 0.0,
                "lag_z": 0.0,
            })
        return {
            "moran_i": 0.0, "expected_i": 0.0, "z_score": 0.0, "p_value": 1.0,
            "clusters": clusters, "scatter": [], "warning": "Varians data nol. Moran tidak dapat dihitung."
        }
        
    # Estimate metric CRS for KNN distances
    crs_metrik = gdf_spasial.estimate_utm_crs()
    gdf_metrik = gdf_spasial.to_crs(crs_metrik).reset_index(drop=True)
    
    w_knn = KNN.from_dataframe(gdf_metrik, k=k, use_index=True)
    w_knn.transform = "R"
    
    # Compute Moran's I
    moran_knn = Moran(nilai_spasial, w_knn, permutations=permutations)
    
    # Compute Local LISA
    lisa_knn = Moran_Local(nilai_spasial, w_knn, permutations=permutations, seed=42)
    
    # Quadrant mapping
    mapping_kuadran = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    
    # Spatial lag
    spatial_lag = lag_spatial(w_knn, nilai_spasial)
    
    # Standardized cases (z-scores)
    z_std = (nilai_spasial - np.mean(nilai_spasial)) / np.std(nilai_spasial, ddof=0)
    lag_z = lag_spatial(w_knn, z_std)
    
    clusters = []
    scatter = []
    
    for idx, r in gdf_spasial.iterrows():
        q = int(lisa_knn.q[idx])
        p_val = float(lisa_knn.p_sim[idx])
        lisa_cluster = mapping_kuadran.get(q, "NS") if p_val < 0.05 else "NS"
        
        item = {
            "kecamatan": r["Kecamatan_Clean"],
            "jumlah_kasus": int(r["jumlah_kasus"]),
            "lat": float(r["lat"]),
            "lng": float(r["lng"]),
            "spatial_lag": round(float(spatial_lag[idx]), 3),
            "lisa_cluster": lisa_cluster,
            "z_score_local": round(float(z_std[idx]), 3),
            "lag_z": round(float(lag_z[idx]), 3),
        }
        clusters.append(item)
        scatter.append({
            "kecamatan": r["Kecamatan_Clean"],
            "x": round(float(z_std[idx]), 3),
            "y": round(float(lag_z[idx]), 3),
            "cluster": lisa_cluster
        })
        
    return {
        "moran_i": round(float(moran_knn.I), 4),
        "expected_i": round(float(moran_knn.EI), 4),
        "z_score": round(float(moran_knn.z_sim), 4),
        "p_value": round(float(moran_knn.p_sim), 4),
        "clusters": clusters,
        "scatter": scatter,
        "warning": "Moran dan LISA dihitung menggunakan esda/libpysal dengan KNN k=5."
    }

