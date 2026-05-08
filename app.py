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

# --- 2. SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=80)
    st.title("ADMIN SISTEM")
    st.markdown(f"**Analis:**\nReza Saputra Azmi")
    st.markdown("**Unit:**\nBiro PBJ Prov. Lampung")
    st.divider()
    file_ren = st.file_uploader("1. Data SIRUP (Perencanaan)", type=['xlsx'])
    file_real = st.file_uploader("2. Data Realisasi (E-Katalog/Daring)", type=['xlsx'])
    st.caption("E-Audit Ultimate v3.1 | 2026")

# --- 3. ENGINE ---
if file_ren and file_real:
    df_ren = pd.read_excel(file_ren)
    df_real = pd.read_excel(file_real)
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    rup_col = 'Kode RUP'
    val_col = 'Total Nilai (Rp)'
    pdn_col = 'Nilai PDN (Rp)'
    satker_col = 'Nama Satuan Kerja'

    if rup_col in df_ren.columns and rup_col in df_real.columns:
        df_ren['ID_RUP_CLEAN'] = df_ren[rup_col].astype(str).apply(clean_rup)
        df_real['ID_RUP_CLEAN'] = df_real[rup_col].astype(str).apply(clean_rup)
        
        df_ren[val_col] = pd.to_numeric(df_ren[val_col], errors='coerce').fillna(0)
        df_real[val_col] = pd.to_numeric(df_real[val_col], errors='coerce').fillna(0)
        if pdn_col in df_real.columns:
            df_real[pdn_col] = pd.to_numeric(df_real[pdn_col], errors='coerce').fillna(0)

        df_join = pd.merge(df_real, df_ren[['ID_RUP_CLEAN', 'Cara Pengadaan', val_col, 'Nama Paket']], 
                           on='ID_RUP_CLEAN', how='left', suffixes=('_REAL', '_REN'))

        def audit_logic(row):
            if not row['ID_RUP_CLEAN']: return "⚠️ KODE RUP KOSONG"
            if pd.isna(row['Nama Paket_REN']): return "⚠️ RUP TIDAK TERDAFTAR"
            if row[f'{val_col}_REAL'] > row[f'{val_col}_REN']: return "⚠️ MELEBIHI PAGU"
            return "✅ VALID"

        df_join['Status Audit'] = df_join.apply(audit_logic, axis=1)
        df_join['Sisa Pagu (Efisiensi)'] = df_join[f'{val_col}_REN'] - df_join[f'{val_col}_REAL']
        df_join.loc[df_join['Status Audit'] == "⚠️ RUP TIDAK TERDAFTAR", 'Sisa Pagu (Efisiensi)'] = 0

        # --- TAMPILAN DASHBOARD ---
        st.title("⚖️ REKONSILIASI & MONITORING PBJ")
        
        k1, k2, k3, k4 = st.columns(4)
        total_real = df_real[val_col].sum()
        
        with k1:
            st.metric("Total Realisasi", f"Rp {total_real/1e9:.2f} M")
        
        with k2:
            if pdn_col in df_real.columns:
                total_pdn = df_real[pdn_col].sum()
                persen_pdn = (total_pdn / total_real * 100) if total_real > 0 else 0
                st.metric("Capaian PDN", f"{persen_pdn:.1f}%")
            else:
                st.metric("Capaian PDN", "N/A")

        with k3:
            efisiensi = df_join[df_join['Status Audit'] == "✅ VALID"]['Sisa Pagu (Efisiensi)'].sum()
            st.metric("Efisiensi Pagu", f"Rp {efisiensi/1e6:.1f} Jt")

        with k4:
            valid_rate = (len(df_join[df_join['Status Audit']=="✅ VALID"]) / len(df_real) * 100) if len(df_real) > 0 else 0
            st.metric("Kepatuhan RUP", f"{valid_rate:.1f}%")

        st.divider()
        search_query = st.text_input("🔍 Cari Nama Paket atau Satuan Kerja...", "")
        
        if search_query:
            df_filtered = df_join[
                df_join['Nama Paket_REAL'].str.contains(search_query, case=False, na=False) |
                df_join[satker_col].str.contains(search_query, case=False, na=False)
            ]
        else:
            df_filtered = df_join

        tab1, tab2 = st.tabs(["📝 Laporan Validasi", "📊 Analisis"])
        with tab1:
            def style_row(val):
                if val == "✅ VALID": return 'background-color: #e1f5e6'
                if val == "⚠️ MELEBIHI PAGU": return 'background-color: #fff3cd'
                return 'background-color: #ffdada'
            st.dataframe(df_filtered.style.applymap(style_row, subset=['Status Audit']), use_container_width=True)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_filtered.to_excel(writer, index=False)
            st.download_button("📥 Unduh Laporan", output.getvalue(), "Laporan_Audit.xlsx")
        with tab2:
            st.table(df_join['Status Audit'].value_counts())
    else:
        st.error("Kolom 'Kode RUP' tidak ditemukan.")
else:
    st.title("⚖️ Sistem Audit Digital PBJ Lampung")
    st.info("Silakan unggah file SIRUP dan E-Katalog untuk memulai.")
