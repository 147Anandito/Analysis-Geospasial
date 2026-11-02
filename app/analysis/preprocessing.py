from __future__ import annotations
import os
import re
from pathlib import Path
import pandas as pd
import numpy as np

DAFTAR_KECAMATAN = [
    "AMBUNTEN", "ARJASA", "BATANG BATANG", "BATUAN", "BATUPUTIH", "BLUTO",
    "DASUK", "DUNGKEK", "GANDING", "GAPURA", "GAYAM", "GILIGENTENG",
    "GULUK GULUK", "KALIANGET", "KANGAYAN", "KOTA SUMENEP", "LENTENG",
    "MANDING", "MASALEMBU", "NONGGUNONG", "PASONGSONGAN", "PRAGAAN",
    "RAAS", "RUBARU", "SAPEKEN", "SARONGGI", "TALANGO"
]

MAPPING_KECAMATAN = {
    "AMBUTEN": "AMBUNTEN",
    "ARJASA PULAU KANGEAN": "ARJASA",
    "ARJASA (PULAU KANGEAN)": "ARJASA",
    "KEPULAUAN ARJASA": "ARJASA",
    "BATANG-BATANG": "BATANG BATANG",
    "BATANGBATANG": "BATANG BATANG",
    "BATU PUTIH": "BATUPUTIH",
    "BATU-PUTIH": "BATUPUTIH",
    "GILI GENTENG": "GILIGENTENG",
    "GILI-GENTENG": "GILIGENTENG",
    "GILI GENTING": "GILIGENTENG",
    "GILI-GENTING": "GILIGENTENG",
    "GILIGENTING": "GILIGENTENG",
    "GILI GENTENG PULAU GILI GENTING": "GILIGENTENG",
    "GILI GENTENG (PULAU GILI GENTING)": "GILIGENTENG",
    "GULUK-GULUK": "GULUK GULUK",
    "GULUKGULUK": "GULUK GULUK",
    "SUMENEP": "KOTA SUMENEP",
    "KECAMATAN KOTA SUMENEP": "KOTA SUMENEP",
    "KOTA": "KOTA SUMENEP",
    "NONG GUNONG": "NONGGUNONG",
    "NONG-GUNONG": "NONGGUNONG"
}

MAPPING_BULAN = {
    "1": 1, "01": 1, "JAN": 1, "JANUARI": 1, "JANUARY": 1,
    "2": 2, "02": 2, "FEB": 2, "FEBRUARI": 2, "FEBRUARY": 2,
    "3": 3, "03": 3, "MAR": 3, "MARET": 3, "MARCH": 3,
    "4": 4, "04": 4, "APR": 4, "APRIL": 4,
    "5": 5, "05": 5, "MEI": 5, "MAY": 5,
    "6": 6, "06": 6, "JUN": 6, "JUNI": 6, "JUNE": 6,
    "7": 7, "07": 7, "JUL": 7, "JULI": 7, "JULY": 7,
    "8": 8, "08": 8, "AGU": 8, "AGUSTUS": 8, "AUG": 8, "AUGUST": 8,
    "9": 9, "09": 9, "SEP": 9, "SEPTEMBER": 9,
    "10": 10, "OKT": 10, "OKTOBER": 10, "OCT": 10, "OCTOBER": 10,
    "11": 11, "NOV": 11, "NOVEMBER": 11,
    "12": 12, "DES": 12, "DESEMBER": 12, "DEC": 12, "DECEMBER": 12
}

def standardisasi_kecamatan(series: pd.Series) -> pd.Series:
    hasil = series.astype("string")
    hasil = (
        hasil
        .str.strip()
        .str.upper()
        .str.replace(r"^(KECAMATAN|KEC\.?)\s+", "", regex=True)
        .str.replace(r"[_]+", " ", regex=True)
        .str.replace(r"\s*-\s*", "-", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )
    hasil = hasil.str.replace(r"\s*\(.+\)", "", regex=True)
    hasil = hasil.str.strip()
    return hasil.map(lambda x: MAPPING_KECAMATAN.get(x, x))

def normalisasi_teks(teks: str) -> str:
    teks = str(teks).strip().upper()
    teks = re.sub(r"[^A-Z0-9]+", " ", teks)
    return re.sub(r"\s+", " ", teks).strip()

def cari_kolom(df: pd.DataFrame, kandidat: list[str], wajib: bool = True) -> str | None:
    mapping_kolom = {normalisasi_teks(c): c for c in df.columns}
    for nama in kandidat:
        nama_normal = normalisasi_teks(nama)
        if nama_normal in mapping_kolom:
            return mapping_kolom[nama_normal]
    if wajib:
        raise ValueError(f"Kolom tidak ditemukan. Kandidat: {kandidat}. Tersedia: {list(df.columns)}")
    return None

def konversi_bulan(series: pd.Series) -> pd.Series:
    bulan_teks = series.astype("string").str.strip().str.upper()
    return bulan_teks.map(MAPPING_BULAN).astype("Int64")

def load_rekap_bulanan(file_path: Path, tahun: int, allow_annual_distribution: bool = True) -> pd.DataFrame:
    if not file_path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")
    
    df = pd.read_excel(file_path, engine="openpyxl")
    
    # Check if first row contains "Kecamatan" to promote headers
    if df.shape[0] > 0 and any(str(x).strip().upper() == "KECAMATAN" for x in df.iloc[0].values):
        new_headers = []
        for col_idx, col_name in enumerate(df.columns):
            row0_val = str(df.iloc[0, col_idx]).strip()
            if row0_val and row0_val != "nan" and row0_val != "None":
                new_headers.append(row0_val)
            else:
                new_headers.append(col_name)
        df.columns = new_headers
        df = df.iloc[1:].reset_index(drop=True)

    df.columns = [str(kolom).strip() for kolom in df.columns]
    
    kolom_kecamatan = cari_kolom(df, kandidat=["Kecamatan", "Nama Kecamatan", "Kec"])
    df = df.rename(columns={kolom_kecamatan: "Kecamatan"})
    df["Kecamatan"] = standardisasi_kecamatan(df["Kecamatan"])
    df = df.dropna(subset=["Kecamatan"]).copy()
    
    kolom_bulan = cari_kolom(df, kandidat=["Bulan", "Month", "Bln"], wajib=False)
    kolom_jumlah = cari_kolom(df, kandidat=["Jumlah Kasus", "Jumlah_Kasus", "Total Kasus", "Kasus", "Jumlah"], wajib=False)
    
    df_long = pd.DataFrame()
    
    if kolom_bulan is not None and kolom_jumlah is not None:
        df_long = df[["Kecamatan", kolom_bulan, kolom_jumlah]].copy()
        df_long = df_long.rename(columns={kolom_bulan: "Bulan", kolom_jumlah: "Jumlah_Kasus"})
        df_long["Bulan"] = konversi_bulan(df_long["Bulan"])
        df_long["Jumlah_Kasus"] = pd.to_numeric(df_long["Jumlah_Kasus"], errors="coerce")
    else:
        kolom_bulan_wide = {}
        for kolom in df.columns:
            teks_kolom = normalisasi_teks(kolom)
            teks_kolom = re.sub(r"\b20\d{2}\b", "", teks_kolom).strip()
            if teks_kolom in MAPPING_BULAN:
                kolom_bulan_wide[kolom] = MAPPING_BULAN[teks_kolom]
                
        if len(kolom_bulan_wide) == 0:
            if kolom_jumlah is not None and allow_annual_distribution:
                df_annual_total = df[["Kecamatan", kolom_jumlah]].copy()
                df_annual_total = df_annual_total.rename(columns={kolom_jumlah: "Jumlah_Kasus"})
                list_of_dfs = []
                for month in range(1, 13):
                    temp_df = df_annual_total.copy()
                    temp_df["Bulan"] = month
                    temp_df["Jumlah_Kasus"] = temp_df["Jumlah_Kasus"] / 12
                    list_of_dfs.append(temp_df)
                df_long = pd.concat(list_of_dfs, ignore_index=True)
                df_long["Jumlah_Kasus"] = pd.to_numeric(df_long["Jumlah_Kasus"], errors="coerce")
            else:
                raise ValueError(f"File tahun {tahun} tidak memiliki kolom bulanan.")
        else:
            kolom_digunakan = ["Kecamatan"] + list(kolom_bulan_wide.keys())
            df_wide = df[kolom_digunakan].copy()
            df_long = df_wide.melt(
                id_vars=["Kecamatan"],
                value_vars=list(kolom_bulan_wide.keys()),
                var_name="Nama_Bulan",
                value_name="Jumlah_Kasus"
            )
            df_long["Bulan"] = df_long["Nama_Bulan"].map(kolom_bulan_wide)
            df_long = df_long.drop(columns=["Nama_Bulan"])
            df_long["Jumlah_Kasus"] = pd.to_numeric(df_long["Jumlah_Kasus"], errors="coerce")
            
    df_long = df_long.dropna(subset=["Kecamatan", "Bulan", "Jumlah_Kasus"]).copy()
    df_long["Bulan"] = df_long["Bulan"].astype(int)
    df_long = df_long[df_long["Bulan"].between(1, 12)].copy()
    df_long["Tahun"] = tahun
    df_long = df_long.groupby(["Kecamatan", "Tahun", "Bulan"], as_index=False)["Jumlah_Kasus"].sum()
    df_long["Jumlah_Kasus"] = df_long["Jumlah_Kasus"].round().astype(int)
    return df_long

def load_detail_2025(file_path: Path) -> pd.DataFrame:
    if not file_path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")
    
    df_raw = pd.read_excel(file_path, engine="openpyxl")
    df_raw.columns = [str(kolom).strip() for kolom in df_raw.columns]
    
    kolom_kecamatan = cari_kolom(df_raw, kandidat=["Kecamatan", "Nama Kecamatan", "Kec"])
    kolom_tanggal = cari_kolom(df_raw, kandidat=["Tanggal Terima", "Tanggal Kejadian", "Tanggal Laporan", "Tanggal", "Date"])
    
    df_raw = df_raw.rename(columns={kolom_kecamatan: "Kecamatan", kolom_tanggal: "Tanggal"})
    df_raw["Kecamatan"] = standardisasi_kecamatan(df_raw["Kecamatan"])
    df_raw["Tanggal"] = pd.to_datetime(df_raw["Tanggal"], errors="coerce", dayfirst=True)
    
    df_clean = df_raw.dropna(subset=["Kecamatan", "Tanggal"]).copy()
    df_clean = df_clean[df_clean["Tanggal"].dt.year == 2025].copy()
    df_clean = df_clean[df_clean["Kecamatan"] != "LUAR DAERAH"].copy()
    
    df_clean["Tahun"] = df_clean["Tanggal"].dt.year
    df_clean["Bulan"] = df_clean["Tanggal"].dt.month
    
    df_m = df_clean.groupby(["Kecamatan", "Tahun", "Bulan"], as_index=False).size().rename(columns={"size": "Jumlah_Kasus"})
    df_m["Jumlah_Kasus"] = df_m["Jumlah_Kasus"].astype(int)
    return df_m

def load_all_data(data_dir: Path) -> dict:
    data_dir = Path(data_dir)
    
    # Cari dengan nama 2022.xlsx atau rekap_campak_2022.xlsx, dll.
    def find_file(prefix_or_year: str) -> Path | None:
        patterns = [f"*{prefix_or_year}*.xlsx", f"*{prefix_or_year}*.xls"]
        for p in patterns:
            found = list(data_dir.glob(p))
            if found:
                return found[0]
        return None

    rekap = []
    for y in [2022, 2023, 2024]:
        p = find_file(str(y))
        if p and p.exists():
            rekap.append(load_rekap_bulanan(p, y))
            
    df_historis = pd.concat(rekap, ignore_index=True) if rekap else pd.DataFrame(columns=["Kecamatan", "Tahun", "Bulan", "Jumlah_Kasus"])
    
    p2025 = find_file("2025")
    df_2025 = pd.DataFrame(columns=["Kecamatan", "Tahun", "Bulan", "Jumlah_Kasus"])
    if p2025 and p2025.exists():
        df_2025 = load_detail_2025(p2025)
        
    df_master = pd.concat([df_historis, df_2025], ignore_index=True)
    
    # Bentuk Balanced Panel
    bulan_terakhir_2025 = int(df_2025["Bulan"].max()) if not df_2025.empty else 12
    periode_awal = pd.Timestamp(year=2022, month=1, day=1)
    periode_akhir = pd.Timestamp(year=2025, month=bulan_terakhir_2025, day=1)
    daftar_periode = pd.date_range(start=periode_awal, end=periode_akhir, freq="MS")
    
    grid = pd.MultiIndex.from_product(
        [DAFTAR_KECAMATAN, daftar_periode],
        names=["Kecamatan", "Periode"]
    ).to_frame(index=False)
    
    grid["Tahun"] = grid["Periode"].dt.year
    grid["Bulan"] = grid["Periode"].dt.month
    
    df_final = grid.merge(df_master, on=["Kecamatan", "Tahun", "Bulan"], how="left")
    df_final["Jumlah_Kasus"] = df_final["Jumlah_Kasus"].fillna(0).astype(int)
    df_final = df_final.sort_values(by=["Kecamatan", "Periode"]).reset_index(drop=True)
    
    return {
        "master_panel": df_final,
        "detail_2025": df_2025
    }

def kecamatan_summary(data: dict, year: int) -> pd.DataFrame:
    df_panel = data["master_panel"]
    df_year = df_panel[df_panel["Tahun"] == year].copy()
    out = df_year.groupby("Kecamatan", as_index=False)["Jumlah_Kasus"].sum().rename(columns={"Jumlah_Kasus": "jumlah_kasus"})
    out = out.rename(columns={"Kecamatan": "kecamatan"})
    return out

