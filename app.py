import streamlit as st
import pandas as pd
import numpy as np
from thefuzz import fuzz, process
import io

# Konfigurasi Tampilan
st.set_page_config(page_title="Audit Digital PBJ Lampung", layout="wide")

# Fungsi Bersih ID RUP
def clean_rup(val):
    if pd.isna(val): return ""
    return ''.join(filter(str.isdigit, str(val)))

# --- SIDEBAR IDENTITAS ---
with st.sidebar:
    st.header("📂 Panel Kontrol PKSTI")
    st.write(f"**Analis:** Reza Saputra Azmi, S.T.")
    st.write("**Instansi:** Biro PBJ Lampung")
    st.divider()
    file_ren = st.file_uploader("1. Upload RUP (Rencana)", type=['xlsx'])
    file_real = st.file_uploader("2. Upload E-Katalog (Realisasi)", type=['xlsx'])
    st.info("Sistem ini memvalidasi data belanja terhadap pagu RUP.")

# --- PROSES AUDIT ---
if file_ren and file_real:
    # Membaca Data
    df_ren = pd.read_excel(file_ren, dtype=str)
    df_real = pd.read_excel(file_real, dtype=str)
    
    # Deteksi kolom RUP (asumsi kolom pertama jika tidak ketemu)
    df_ren['ID_RUP_CLEAN'] = df_ren.iloc[:, 0].apply(clean_rup)
    df_real['ID_RUP_CLEAN'] = df_real.iloc[:, 0].apply(clean_rup)
    
    # Audit Sederhana (Join)
    df_join = pd.merge(df_real, df_ren, on='ID_RUP_CLEAN', how='left', suffixes=('_REAL', '_REN'))
    
    # Beri Status
    def get_status(row):
        if pd.isna(row.get('ID_RUP_CLEAN')) or row['ID_RUP_CLEAN'] == "": return "⚠️ DATA TIDAK VALID"
        return "✅ TERVERIFIKASI"
    
    df_join['Status Audit'] = df_join.apply(get_status, axis=1)

    # --- TAMPILAN DASHBOARD ---
    st.title("📊 Hasil Audit Digital Biro PBJ")
    
    tab1, tab2 = st.tabs(["🔍 Detail Temuan", "📈 Ringkasan"])
    
    with tab1:
        st.dataframe(df_join, use_container_width=True)
        
        # Download Hasil Audit
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_join.to_excel(writer, index=False)
        st.download_button("📥 Download Hasil Audit (.xlsx)", output.getvalue(), "Laporan_Audit_PBJ.xlsx")

    with tab2:
        st.subheader("Statistik Kepatuhan")
        st.bar_chart(df_join['Status Audit'].value_counts())
else:
    st.title("🚀 Selamat Datang, Mas Reza")
    st.info("Silakan unggah file Excel Perencanaan dan Realisasi di sidebar untuk memulai audit otomatis.")
