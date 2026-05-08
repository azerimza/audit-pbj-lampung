import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #0c2461; color: white; }
    [data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 700 !important; color: #0c2461 !important; }
    [data-testid="stMetricLabel"] { font-size: 14px !important; color: #6c757d !important; }
    .stMetric { background-color: #ffffff; padding: 15px !important; border-radius: 10px; border: 1px solid #e0e0e0; }
    h1 { color: #0c2461; font-size: 26px !important; }
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
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=60)
    st.markdown("### **ADMIN SISTEM**")
    st.markdown(f"**Analis:** Reza Saputra Azmi")
    st.markdown("**Unit:** Biro PBJ Prov. Lampung")
    st.divider()
    file_ren = st.file_uploader("1. Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("2. Data Realisasi (CSV)", type=['csv'])
    st.caption("E-Audit Stable v3.5")

# --- 3. ENGINE ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    # Mapping Kolom
    rup_col, val_col, pdn_col, method_col = 'Kode RUP', 'Total Nilai (Rp)', 'Nilai PDN (Rp)', 'Metode Pengadaan'

    if rup_col in df_ren.columns and rup_col in df_real.columns:
        df_ren['ID_RUP_CLEAN'] = df_ren[rup_col].astype(str).apply(clean_rup)
        df_real['ID_RUP_CLEAN'] = df_real[rup_col].astype(str).apply(clean_rup)
        
        # Bersihkan Angka
        for d in [df_ren, df_real]:
            if val_col in d.columns:
                d[val_col] = pd.to_numeric(d[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)
        
        df_join = pd.merge(df_real, df_ren[['ID_RUP_CLEAN', 'Cara Pengadaan', val_col, 'Nama Paket']], 
                           on='ID_RUP_CLEAN', how='left', suffixes=('_REAL', '_REN'))

        # Logika Audit
        def audit_logic(row):
            if not row['ID_RUP_CLEAN'] or row['ID_RUP_CLEAN'] == "": return "⚠️ KODE RUP KOSONG"
            if pd.isna(row['Nama Paket_REN']): return "⚠️ RUP TIDAK TERDAFTAR"
            return "✅ VALID" if row[f'{val_col}_REAL'] <= row[f'{val_col}_REN'] else "⚠️ MELEBIHI PAGU"

        df_join['Status Audit'] = df_join.apply(audit_logic, axis=1)

        # --- 4. TAMPILAN DASHBOARD ---
        st.markdown("# ⚖️ DASHBOARD REKONSILIASI PBH")
        
        # KPI Bar (Metrik Utama)
        k1, k2, k3, k4 = st.columns(4)
        total_real = df_real[val_col].sum()
        k1.metric("Total Realisasi", f"Rp {total_real/1e9:.2f} M")
        
        valid_data = df_join[df_join['Status Audit']=="✅ VALID"]
        efisiensi = valid_data[f'{val_col}_REN'].sum() - valid_data[f'{val_col}_REAL'].sum()
        k2.metric("Efisiensi Pagu", f"Rp {efisiensi/1e6:.1f} Jt" if efisiensi < 1e9 else f"Rp {efisiensi/1e9:.2f} M")
        
        k3.metric("Kepatuhan RUP", f"{(len(valid_data)/len(df_real)*100):.1f}%")
        k4.metric("Total Paket", f"{len(df_real)} Paket")

        st.divider()

        # --- 5. FILTER METODE (FITUR BARU) ---
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            # Ambil daftar metode unik dari kolom 'Metode Pengadaan'
            if method_col in df_join.columns:
                list_metode = ["Semua Metode"] + sorted(df_join[method_col].unique().tolist())
                pilihan_metode = st.selectbox("🎯 Pilih Metode Pengadaan:", list_metode)
            else:
                st.warning("Kolom 'Metode Pengadaan' tidak ditemukan.")
                pilihan_metode = "Semua Metode"

        with col_f2:
            search = st.text_input("🔍 Cari Nama Paket...", "")

        # Terapkan Filter
        df_f = df_join.copy()
        if pilihan_metode != "Semua Metode":
            df_f = df_f[df_f[method_col] == pilihan_metode]
        if search:
            df_f = df_f[df_f['Nama Paket_REAL'].str.contains(search, case=False, na=False)]

        # --- 6. TAMPILAN DATA ---
        st.markdown(f"### 📋 Laporan: {pilihan_metode}")
        
        def style_r(v):
            color = '#e1f5e6' if v == "✅ VALID" else '#fff3cd' if v == "⚠️ MELEBIHI PAGU" else '#ffdada'
            return f'background-color: {color}'
        
        st.dataframe(df_f.style.map(style_r, subset=['Status Audit']), use_container_width=True)
        
        # Download Berdasarkan Hasil Filter
        output = io.BytesIO()
        df_f.to_excel(output, index=False)
        st.download_button(f"📥 Ekspor Data {pilihan_metode} (.xlsx)", output.getvalue(), f"Audit_{pilihan_metode}.xlsx")

    else:
        st.error("Format kolom 'Kode RUP' tidak ditemukan.")
else:
    st.markdown("# ⚖️ Sistem Audit Digital PBJ")
    st.info("Silakan unggah file CSV SIRUP dan E-Katalog di sidebar untuk memulai.")
