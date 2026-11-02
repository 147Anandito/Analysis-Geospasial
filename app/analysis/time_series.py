import pandas as pd

def timeseries_data(data: dict) -> dict:
    df_panel = data["master_panel"]
    
    # Annual cases
    ann_df = df_panel.groupby("Tahun", as_index=False)["Jumlah_Kasus"].sum()
    annual = [{"tahun": int(r["Tahun"]), "jumlah_kasus": int(r["Jumlah_Kasus"])} for _, r in ann_df.iterrows()]
    
    # Monthly cases
    mon_df = df_panel.groupby(["Tahun", "Bulan"], as_index=False)["Jumlah_Kasus"].sum()
    monthly_records = [
        {"tahun": int(r["Tahun"]), "bulan": int(r["Bulan"]), "jumlah_kasus": int(r["Jumlah_Kasus"])}
        for _, r in mon_df.iterrows()
    ]
    
    return {"annual": annual, "monthly": monthly_records}