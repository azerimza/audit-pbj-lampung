import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- 1. CONFIG & CSS ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .metric-card {
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 10px solid #0c2461; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-label { font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; }
    .metric-value { font-size: 26px; color: #0c2461; font-weight: bold; font-family: 'Consolas', monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ENGINE ---
def read_csv_smart(file):
    try:
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
    except:
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='cp1252')

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=50)
    st.title("Admin Audit")
    st.markdown("**Reza Saputra Azmi**")
    st.divider()
    file_ren = st.file_uploader("Upload Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("Upload Data Realisasi (CSV)", type=['csv'])

if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col = 'Total Nilai (Rp)'
    sumber_col = 'Sumber Transaksi'

    # Cleaning & Processing
    df_real[val_col] = pd.to_numeric(df_real[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)
    df_ren[val_col] = pd.to_numeric(df_ren[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)
    
    is_tokodaring = df_real[sumber_col].str.contains('Tokodaring|Toko Daring', case=False, na=False)
    df_td = df_real[is_tokodaring].copy()
    df_kat = df_real[~is_tokodaring].copy()

    # --- UI ---
    st.markdown("# ⚖️ Laporan Audit PBJ Digital")
    
    # Tombol Export di Baris Atas
    col_exp1, col_exp2 = st.columns(2)
    
    # Logika Export Excel
    output_xlsx = io.BytesIO()
    with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer:
        df_real.to_excel(writer, sheet_name='Data_Realisasi', index=False)
        df_ren.to_excel(writer, sheet_name='Data_Rencana', index=False)
    
    col_exp1.download_button(
        label="📥 Download Laporan Excel",
        data=output_xlsx.getvalue(),
        file_name=f"Audit_PBJ_Lampung_{datetime.now().strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.ms-excel"
    )

    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">TOTAL PAGU RENCANA</div>
        <div class="metric-value">Rp {df_ren[val_col].sum():,.0f}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="metric-card" style="border-left-color: #007bff;">
        <div class="metric-label">REALISASI E-KATALOG (5.0 & 6.0)</div>
        <div class="metric-value">Rp {df_kat[val_col].sum():,.0f}</div>
        <div style="font-size:12px; color:gray;">Total: {len(df_kat)} Paket</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="metric-card" style="border-left-color: #ff9900;">
        <div class="metric-label">REALISASI TOKODARING</div>
        <div class="metric-value">Rp {df_td[val_col].sum():,.0f}</div>
        <div style="font-size:12px; color:gray;">Total: {len(df_td)} Paket</div>
    </div>""", unsafe_allow_html=True)

else:
    st.info("Unggah file untuk mengaktifkan fitur ekspor laporan.")
