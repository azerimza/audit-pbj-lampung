import streamlit as st
import pandas as pd
import numpy as np

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .metric-card {
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 10px solid #0c2461; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-label { font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
    .metric-value { font-size: 28px; color: #0c2461; font-weight: bold; font-family: 'Consolas', monospace; }
    .sub-info { font-size: 14px; color: #888; margin-top: 5px; }
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
    st.title("Audit PBJ")
    st.markdown("**Reza Saputra Azmi**")
    st.divider()
    file_ren = st.file_uploader("Upload Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("Upload Data Realisasi (CSV)", type=['csv'])

# --- 3. ENGINE ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    df_real.columns = df_real.columns.str.strip()
    
    val_col = 'Total Nilai (Rp)'
    sumber_col = 'Sumber Transaksi' 

    if val_col in df_real.columns and sumber_col in df_real.columns:
        # Bersihkan angka (menghilangkan Rp, titik, koma agar jadi angka murni)
        df_real[val_col] = pd.to_numeric(df_real[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)
        df_ren[val_col] = pd.to_numeric(df_ren[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

        # --- LOGIKA FILTER EKSKLUSI ---
        # 1. Tokodaring (Spesifik)
        is_tokodaring = df_real[sumber_col].str.contains('Tokodaring|Toko Daring', case=False, na=False)
        df_td = df_real[is_tokodaring]
        
        # 2. E-Katalog (Semua Realisasi yang BUKAN Tokodaring)
        df_kat = df_real[~is_tokodaring]

        # --- UI DISPLAY (VERTIKAL & DETAIL) ---
        st.markdown("# ⚖️ Laporan Realisasi Anggaran Detail")

        # TOTAL PAGU
        st.markdown(f"""<div class="metric-card" style="border-left-color: #0c2461;">
            <div class="metric-label">TOTAL PAGU RENCANA (SIRUP)</div>
            <div class="metric-value">Rp {df_ren[val_col].sum():,.0f}</div>
        </div>""", unsafe_allow_html=True)

        # REALISASI E-KATALOG (Hasil Eksklusi Tokodaring)
        st.markdown(f"""<div class="metric-card" style="border-left-color: #007bff;">
            <div class="metric-label">REALISASI E-KATALOG (5.0, 6.0 & Lainnya)</div>
            <div class="metric-value">Rp {df_kat[val_col].sum():,.0f}</div>
            <div class="sub-info">Total: {len(df_kat)} Paket (Semua transaksi selain Tokodaring)</div>
        </div>""", unsafe_allow_html=True)

        # REALISASI TOKODARING
        st.markdown(f"""<div class="metric-card" style="border-left-color: #ff9900;">
            <div class="metric-label">REALISASI TOKODARING</div>
            <div class="metric-value">Rp {df_td[val_col].sum():,.0f}</div>
            <div class="sub-info">Total: {len(df_td)} Paket</div>
        </div>""", unsafe_allow_html=True)

        # SISA ANGGARAN
        total_real = df_real[val_col].sum()
        total_pagu = df_ren[val_col].sum()
        sisa = total_pagu - total_real
        sisa_color = "#28a745" if sisa >= 0 else "#dc3545"

        st.markdown(f"""<div class="metric-card" style="border-left-color: {sisa_color};">
            <div class="metric-label">SISA PAGU ANGGARAN</div>
            <div class="metric-value">Rp {sisa:,.0f}</div>
            <div class="sub-info">Status: {"Aman (Efisiensi)" if sisa >= 0 else "Overbudget"}</div>
        </div>""", unsafe_allow_html=True)

    else:
        st.error(f"Kolom '{sumber_col}' atau '{val_col}' tidak ditemukan.")
else:
    st.info("Menunggu data diunggah untuk memulai proses audit.")
