import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    [data-testid="stSidebar"] { background-color: #0c2461; color: white; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 5px solid #0c2461;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    h1, h2, h3 { color: #0c2461; font-family: 'Segoe UI', sans-serif; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

def clean_rup(val):
    if pd.isna(val) or val == "": return ""
    return ''.join(filter(str.isdigit, str(val)))

# Fungsi Spesial Membaca CSV (Mendeteksi Pemisah Otomatis)
def read_csv_smart(file):
    try:
        # Coba baca dengan koma
        df = pd.read_csv(file, sep=',', encoding='utf-8')
        if len(df.columns) <= 1: # Jika gagal membagi kolom
            file.seek(0)
            df = pd.read_csv(file, sep=';', encoding='utf-8')
    except:
        file.seek(0)
        df = pd.read_csv(file, sep=';', encoding='cp1252') # Alternatif encoding
    return df

# --- 2. SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=80)
    st.title("ADMIN SISTEM")
    st.markdown(f"**Analis:**\nReza Saputra Azmi")
    st.markdown("**Unit:**\nBiro PBJ Prov. Lampung")
    st.divider()
    
    st.subheader("📁 UPLOAD FILE (.CSV)")
    file_ren = st.file_uploader("1. Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("2. Data Realisasi (CSV)", type=['csv'])
    
    st.divider()
    st.caption("E-Audit CSV v3.2 | 2026")

# --- 3. ENGINE ---
if file_ren and file_real:
    df_ren = read_csv_smart(file_ren)
    df_real = read_csv_smart(file_real)
    
    # Bersihkan spasi di nama kolom
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    rup_col = 'Kode RUP'
    val_col = 'Total Nilai (Rp)'
    pdn_col = 'Nilai PDN (Rp)'
    satker_col = 'Nama Satuan Kerja'

    if rup_col in df_ren.columns and rup_col in df_real.columns:
        df_ren['ID_RUP_CLEAN'] = df_ren[rup_col].astype(str).apply(clean_rup)
        df_real['ID_RUP_CLEAN'] = df_real[rup_col].astype(str).apply(clean_rup)
        
        # Bersihkan format mata uang jika ada (misal: "Rp 1.000")
        for col in [df_ren, df_real]:
            if val_col in col.columns:
                col[val_col] = col[val_col].astype(str).str.replace(r'[^0-9]', '', regex=True)
                col[val_col] = pd.to_numeric(col[val_col], errors='coerce').fillna(0)
        
        if pdn_col in df_real.columns:
            df_real[pdn_col] = df_real[pdn_col].astype(str).str.replace(r'[^0-9]', '', regex=True)
            df_real[pdn_col] = pd.to_numeric(df_real[pdn_col], errors='coerce').fillna(0)

        df_join = pd.merge(df_real, df_ren[['ID_RUP_CLEAN', 'Cara Pengadaan', val_col, 'Nama Paket']], 
                           on='ID_RUP_CLEAN', how='left', suffixes=('_REAL', '_REN'))

        def audit_logic(row):
            if not row['ID_RUP_CLEAN']: return "⚠️ KODE RUP KOSONG"
            if pd.isna(row['Nama Paket_REN']): return "⚠️ RUP TIDAK TERDAFTAR"
            if row[f'{val_col}_REAL'] > row[f'{val_col}_REN']: return "⚠️ MELEBIHI PAGU"
            return "✅ VALID"

        df_join['Status Audit'] = df_join.apply(audit_logic, axis=1)

        # --- TAMPILAN DASHBOARD ---
        st.title("⚖️ REKONSILIASI PBJ (MODE CSV)")
        
        k1, k2, k3, k4 = st.columns(4)
        total_real = df_real[val_col].sum()
        
        with k1:
            st.metric("Total Realisasi", f"Rp {total_real/1e9:.2f} M")
        with k2:
            if pdn_col in df_real.columns:
                total_pdn = df_real[pdn_col].sum()
                p_pdn = (total_pdn/total_real*100) if total_real > 0 else 0
                st.metric("Capaian PDN", f"{p_pdn:.1f}%")
            else: st.metric("Capaian PDN", "N/A")
        with k3:
            efisiensi = (df_join[df_join['Status Audit']=="✅ VALID"][f'{val_col}_REN'].sum()) - (df_join[df_join['Status Audit']=="✅ VALID"][f'{val_col}_REAL'].sum())
            st.metric("Efisiensi Pagu", f"Rp {efisiensi/1e6:.1f} Jt")
        with k4:
            valid_rate = (len(df_join[df_join['Status Audit']=="✅ VALID"]) / len(df_real) * 100) if len(df_real) > 0 else 0
            st.metric("Kepatuhan RUP", f"{valid_rate:.1f}%")

        st.divider()
        search = st.text_input("🔍 Cari Paket atau Satker...", "")
        if search:
            df_f = df_join[df_join['Nama Paket_REAL'].str.contains(search, case=False, na=False) | 
                           df_join[satker_col].str.contains(search, case=False, na=False)]
        else: df_f = df_join

        tab1, tab2 = st.tabs(["📝 Laporan Validasi", "📊 Statistik"])
        with tab1:
            def style_r(v):
                if v == "✅ VALID": return 'background-color: #e1f5e6'
                if v == "⚠️ MELEBIHI PAGU": return 'background-color: #fff3cd'
                return 'background-color: #ffdada'
            st.dataframe(df_f.style.applymap(style_r, subset=['Status Audit']), use_container_width=True)
            
            output = io.BytesIO()
            df_f.to_excel(output, index=False)
            st.download_button("📥 Unduh Hasil (.xlsx)", output.getvalue(), "Laporan_Audit.xlsx")
        with tab2:
            st.bar_chart(df_join['Status Audit'].value_counts())
    else:
        st.error(f"Kolom '{rup_col}' tidak ditemukan. Periksa apakah file CSV menggunakan pemisah koma (,) atau titik koma (;).")
else:
    st.title("⚖️ Sistem Audit Digital PBJ Lampung")
    st.info("Silakan unggah file CSV SIRUP dan E-Katalog.")
