import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. KONFIGURASI HALAMAN & THEME ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

# CSS untuk tampilan Navy Blue & Metrik Premium
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
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
        padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNGSI MEMBERSIHKAN DATA ---
def clean_rup(val):
    if pd.isna(val) or val == "": return ""
    return ''.join(filter(str.isdigit, str(val)))

# --- 3. SIDEBAR (ADMINISTRATOR SISTEM) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=80)
    st.title("ADMIN SISTEM")
    st.markdown(f"**Analis:**\nReza Saputra Azmi")
    st.markdown("**Unit:**\nBiro PBJ Prov. Lampung")
    st.divider()
    
    st.subheader("📁 SUMBER DATA")
    file_ren = st.file_uploader("1. Data SIRUP (Perencanaan)", type=['xlsx'])
    file_real = st.file_uploader("2. Data Realisasi (E-Katalog/Daring)", type=['xlsx'])
    
    st.divider()
    st.info("💡 Tip: Pastikan kolom 'Kode RUP' dan 'Total Nilai (Rp)' tersedia di kedua file.")
    st.caption("E-Audit Ultimate v3.0 | 2026")

# --- 4. ENGINE REKONSILIASI ---
if file_ren and file_real:
    # Membaca data
    df_ren = pd.read_excel(file_ren)
    df_real = pd.read_excel(file_real)

    # Pre-processing: Bersihkan spasi di nama kolom
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    # Identifikasi Nama Kolom Kunci
    rup_col = 'Kode RUP'
    val_col = 'Total Nilai (Rp)'
    pdn_col = 'Nilai PDN (Rp)'
    satker_col = 'Nama Satuan Kerja'

    if rup_col in df_ren.columns and rup_col in df_real.columns:
        # 4a. Cleaning ID RUP & Anggaran
        df_ren['ID_RUP_CLEAN'] = df_ren[rup_col].astype(str).apply(clean_rup)
        df_real['ID_RUP_CLEAN'] = df_real[rup_col].astype(str).apply(clean_rup)
        
        df_ren[val_col] = pd.to_numeric(df_ren[val_col], errors='coerce').fillna(0)
        df_real[val_col] = pd.to_numeric(df_real[val_col], errors='coerce').fillna(0)
        if pdn_col in df_real.columns:
            df_real[pdn_col] = pd.to_numeric(df_real[pdn_col], errors='coerce').fillna(0)

        # 4b. Merging (Left Join Realisasi ke Rencana)
        df_join = pd.merge(
            df_real, 
            df_ren[['ID_RUP_CLEAN', 'Cara Pengadaan', val_col, 'Nama Paket']], 
            on='ID_RUP_CLEAN', 
            how='left', 
            suffixes=('_REAL', '_REN')
        )

        # 4c. Logika Validasi & Sisa Pagu
        def audit_logic(row):
            if not row['ID_RUP_CLEAN']: return "⚠️ KODE RUP KOSONG"
            if pd.isna(row['Nama Paket_REN']): return "⚠️ RUP TIDAK TERDAFTAR"
            if row[f'{val_col}_REAL'] > row[f'{val_col}_REN']: return "⚠️ MELEBIHI PAGU"
            return "✅ VALID"

        df_join['Status Audit'] = df_join.apply(audit_logic, axis=1)
        df_join['Sisa Pagu (Efisiensi)'] = df_join[f'{val_col}_REN'] - df_join[f'{val_col}_REAL']
        # Sisa pagu hanya dihitung jika data VALID/Ada di RUP
        df_join.loc[df_join['Status Audit'] == "⚠️ RUP TIDAK TERDAFTAR", 'Sisa Pagu (Efisiensi)'] = 0

        # --- 5. TAMPILAN DASHBOARD UTAMA ---
        st.title("⚖️ REKONSILIASI & MONITORING PBN")
        st.write("Sistem Monitoring Realisasi dan Capaian PDN - Biro PBJ Lampung")

        # 5a. Metrik Pimpinan (KPI)
        k1, k2, k3, k4 = st.columns(4)
        
        total_real = df_real[val_col].sum()
        with k1:
            st.metric("Total Realisasi", f"Rp {total_real/1e9:.2f} M")
        
        with k2:
            if pdn_col in df_real.columns:
                total_pdn = df_real[pdn_col].sum()
                persen_pdn = (total_pdn / total_real * 100) if total_real > 0 else 0
                st.metric("Capaian PDN", f"{pers
