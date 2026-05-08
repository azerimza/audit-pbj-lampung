import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

# CSS Kartu Vertikal
st.markdown("""
    <style>
    .metric-card {
        background-color: white; padding: 18px; border-radius: 10px;
        border-left: 8px solid #0c2461; box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 12px;
    }
    .metric-label { font-size: 13px; color: #555; font-weight: bold; text-transform: uppercase; }
    .metric-value { font-size: 22px; color: #0c2461; font-weight: bold; font-family: 'Consolas', monospace; }
    .sub-label { font-size: 12px; color: #888; }
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
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=50)
    st.title("Admin Audit")
    st.markdown("**Reza Saputra Azmi**")
    st.divider()
    file_ren = st.file_uploader("1. Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("2. Data Realisasi (CSV)", type=['csv'])

# --- 3. ENGINE ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()
    
    val_col = 'Total Nilai (Rp)'
    metode_col = 'Metode Pengadaan'

    # Clean Data
    for d in [df_ren, df_real]:
        if val_col in d.columns:
            d[val_col] = pd.to_numeric(d[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # --- LOGIKA PEMISAHAN ---
    # Katalog (5.0, 6.0, atau hanya kata 'Katalog')
    df_katalog = df_real[df_real[metode_col].str.contains('Katalog', case=False, na=False)]
    
    # Toko Daring
    df_tokodaring = df_real[df_real[metode_col].str.contains('Tokodaring|Toko Daring', case=False, na=False)]

    # Total Perencanaan
    total_ren = df_ren[val_col].sum()
    
    # --- TAMPILAN DASHBOARD ---
    st.markdown("# ⚖️ Pemisahan Realisasi Katalog & Toko Daring")
    
    # KARTU 1: RENCANA
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">TOTAL PAGU RENCANA (SIRUP)</div>
        <div class="metric-value">Rp {total_ren:,.0f}</div>
    </div>""", unsafe_allow_html=True)

    # KARTU 2: KATALOG
    st.markdown(f"""<div class="metric-card" style="border-left-color: #1e90ff;">
        <div class="metric-label">REALISASI E-KATALOG (5.0 & 6.0)</div>
        <div class="metric-value">Rp {df_katalog[val_col].sum():,.0f}</div>
        <div class="sub-label">Total: {len(df_katalog)} Paket</div>
    </div>""", unsafe_allow_html=True)

    # KARTU 3: TOKO DARING
    st.markdown(f"""<div class="metric-card" style="border-left-color: #ffa500;">
        <div class="metric-label">REALISASI TOKO DARING</div>
        <div class="metric-value">Rp {df_tokodaring[val_col].sum():,.0f}</div>
        <div class="sub-label">Total: {len(df_tokodaring)} Paket</div>
    </div>""", unsafe_allow_html=True)

    # KARTU 4: SISA TOTAL
    total_real_all = df_real[val_col].sum()
    total_sisa = total_ren - total_real_all
    sisa_color = "#2ecc71" if total_sisa >= 0 else "#e74c3c"
    
    st.markdown(f"""<div class="metric-card" style="border-left-color: {sisa_color};">
        <div class="metric-label">SISA ANGGARAN KESELURUHAN</div>
        <div class="metric-value">Rp {total_sisa:,.0f}</div>
        <div class="sub-label">Status: {"Efisiensi" if total_sisa >= 0 else "Overbudget"}</div>
    </div>""", unsafe_allow_html=True)

    st.divider()
    
    # Tabel Detail Pemisahan
    t1, t2 = st.tabs(["📋 Data Katalog", "🛒 Data Toko Daring"])
    with t1:
        st.dataframe(df_katalog[['Nama Satuan Kerja', 'Nama Paket', val_col]], use_container_width=True)
    with t2:
        st.dataframe(df_tokodaring[['Nama Satuan Kerja', 'Nama Paket', val_col]], use_container_width=True)

else:
    st.info("Unggah file CSV untuk memisahkan data Katalog dan Toko Daring.")
