import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

# CSS khusus untuk membuat kartu metrik vertikal yang estetik
st.markdown("""
    <style>
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 8px solid #0c2461;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .metric-label { font-size: 14px; color: #666; font-weight: bold; }
    .metric-value { font-size: 24px; color: #0c2461; font-weight: bold; font-family: 'Courier New'; }
    .metric-delta-pos { color: green; font-size: 14px; }
    .metric-delta-neg { color: red; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def clean_rup(val):
    if pd.isna(val) or val == "": return ""
    return ''.join(filter(str.isdigit, str(val)))

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
    st.title("Admin Sistem")
    st.markdown("**Reza Saputra Azmi**")
    st.divider()
    file_ren = st.file_uploader("1. Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("2. Data Realisasi (CSV)", type=['csv'])

# --- 3. ENGINE ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col = 'Total Nilai (Rp)'

    # Pembersihan Angka
    for d in [df_ren, df_real]:
        if val_col in d.columns:
            d[val_col] = pd.to_numeric(d[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # Hitung Total
    total_ren = df_ren[val_col].sum()
    total_real = df_real[val_col].sum()
    total_sisa = total_ren - total_real
    persen_serap = (total_real/total_ren*100) if total_ren > 0 else 0

    # --- TAMPILAN UTAMA ---
    st.markdown("# ⚖️ Ringkasan Audit Anggaran")
    
    # KARTU 1: PAGU (VERTIKAL)
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">TOTAL PAGU RENCANA (SIRUP)</div>
            <div class="metric-value">Rp {total_ren:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)

    # KARTU 2: REALISASI (VERTIKAL)
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">TOTAL REALISASI (E-KATALOG/TOKO DARING)</div>
            <div class="metric-value">Rp {total_real:,.0f}</div>
            <div class="metric-delta-pos">↑ {persen_serap:.2f}% Penyerapan Terdeteksi</div>
        </div>
    """, unsafe_allow_html=True)

    # KARTU 3: SISA (VERTIKAL)
    sisa_class = "metric-delta-pos" if total_sisa >= 0 else "metric-delta-neg"
    sisa_label = "SISA ANGGARAN (EFISIENSI)" if total_sisa >= 0 else "DEFISIT ANGGARAN (OVERBUDGET)"
    
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{sisa_label}</div>
            <div class="metric-value">Rp {total_sisa:,.0f}</div>
            <div class="{sisa_class}">{"Status: Aman" if total_sisa >= 0 else "🚨 Perlu Audit Segera"}</div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📑 Detail Data")
    st.dataframe(df_real.head(10), use_container_width=True)

else:
    st.info("Silakan unggah data CSV untuk melihat kartu laporan.")
