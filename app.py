import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="REKONSILIASI DATA", layout="wide")

st.markdown("""
    <style>
    .stat-card {
        background-color: #ffffff; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 5px solid #0c2461;
        text-align: center; margin-bottom: 20px;
    }
    .stat-label { font-size: 14px; color: #555; font-weight: bold; }
    .stat-value { font-size: 24px; color: #0c2461; font-weight: bold; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def read_csv_smart(file):
    try:
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
    except:
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='cp1252')

# --- 2. SIDEBAR ---
with st.sidebar:
    col1, col2, col3 = st.columns([1, 2, 1]) 
    with col2:
        try:
            st.image("LOGO PEMPROV BARU.png", width=60)
        except:
            st.warning("Logo tidak ditemukan")
            
    st.markdown("<h3 style='text-align: center; margin-top: -10px;'>PEMBINAAN DAN ADVOKASI</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'><b>Reza Saputra Azmi</b></p>", unsafe_allow_html=True)
    st.divider()
    
    file_ren = st.file_uploader("1. Upload Data SIRUP", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])

# --- 3. LOGIKA PEMROSESAN ---
if file_ren and file_real:
    df_ren_raw, df_real_raw = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col, rup_col, satker_col = 'Total Nilai (Rp)', 'Kode RUP', 'Nama Satuan Kerja'
    
    # Bersihkan nama kolom
    df_ren_raw.columns = df_ren_raw.columns.str.strip()
    df_real_raw.columns = df_real_raw.columns.str.strip()

    # Paksa Kode RUP jadi String & Bersihkan Spasi
    df_ren_raw[rup_col] = df_ren_raw[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)
    df_real_raw[rup_col] = df_real_raw[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    # Sinkronisasi Nama Satker agar pencocokan teks antar-file tidak miss
    df_ren_raw[satker_col] = df_ren_raw[satker_col].astype(str).str.strip()
    df_real_raw[satker_col] = df_real_raw[satker_col].astype(str).str.strip()

    for df in [df_ren_raw, df_real_raw]:
        if val_col in df.columns:
            df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # =====================================================================
    # PEMISAHAN LOGIKAL: SWAKELOLA vs PENYEDIA SEJAK AWAL
    # =====================================================================
    # 1. Dataset Jalur Swakelola
    df_ren_swa = df_ren_raw[df_ren_raw['Metode Pengadaan'].astype(str).str.lower().str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_ren_raw.columns else pd.DataFrame(columns=df_ren_raw.columns)
    df_real_swa = df_real_raw[df_real_raw['Metode Pengadaan'].astype(str).str.lower().str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_real_raw.columns else pd.DataFrame(columns=df_real_raw.columns)

    # 2. Dataset Jalur Penyedia (Tanpa Swakelola)
    df_ren = df_ren_raw[~df_ren_raw['Metode Pengadaan'].astype(str).str.lower().str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_ren_raw.columns else df_ren_raw.copy()
    df_real = df_real_raw[~df_real_raw['Metode Pengadaan'].astype(str).str.lower().str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_real_raw.columns else df_real_raw.copy()

    # Identifikasi Kategori Khusus Penyedia
    def map_kat(m):
        m = str(m).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Tokodaring'
        if 'katalog' in m: return 'E-Katalog'
        return 'Penyedia Lainnya'

    df_real['Kat_Audit'] = df_real['Metode Pengadaan'].apply(map_kat) if 'Metode Pengadaan' in df_real.columns else 'Lainnya'
    
    # Agregasi data realisasi penyedia berdasarkan RUP & Satker
    df_real_agg = df_real.groupby([rup_col, satker_col]).agg({
        val_col: 'sum', 'Kat_Audit': 'first'
    }).reset_index()

    # --- 4. PANEL FILTER UTAMA ---
    st.title("📊 Dashboard Audit & Rekonsiliasi (Terpisah Per Jalur)")
    
    f1,
