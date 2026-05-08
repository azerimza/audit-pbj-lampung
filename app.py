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
    h1 { color: #0c2461; font-size: 24px !important; }
    /* Memastikan tabel terlihat bersih */
    .stDataFrame { border: 1px solid #e0e0e0; border-radius: 10px; }
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
    st.caption("E-Audit Rekap v4.5")

# --- 3. CORE ENGINE ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    rup_col, val_col = 'Kode RUP', 'Total Nilai (Rp)'

    if rup_col in df_ren.columns and rup_col in df_real.columns:
        # Pre-processing
        df_ren['ID_RUP_CLEAN'] = df_ren[rup_col].astype(str).apply(clean_rup)
        df_real['ID_RUP_CLEAN'] = df_real[rup_col].astype(str).apply(clean_rup)
        
        for d in [df_ren, df_real]:
            if val_col in d.columns:
                d[val_col] = pd.to_numeric(d[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

        # Agregasi Realisasi per RUP
        df_real_agg = df_real.groupby('ID_RUP_CLEAN', as_index=False).agg({
            val_col: 'sum',
            'Nama Satuan Kerja': 'first',
            'Metode Pengadaan': 'first'
        }).rename(columns={val_col: 'Anggaran_Realisasi'})

        # Join untuk identifikasi Match/Mismatch
        df_master = pd.merge(df_ren[['ID_RUP_CLEAN', 'Nama Satuan Kerja', 'Cara Pengadaan', val_col]], 
                            df_real_agg, on='ID_RUP_CLEAN', how='outer', indicator=True)
        df_master['Satker_Final'] = df_master['Nama Satuan Kerja_x'].combine_first(df_master['Nama Satuan Kerja_y'])

        # --- TAMPILAN DASHBOARD ---
        st.markdown("# ⚖️ REKONSILIASI PERENCANAAN & REALISASI")
        
        t1, t2 = st.tabs(["📊 Analisis Data Detail", "📑 Laporan Rekapitulasi Satker"])

        with t1:
            st.info("Pilih kondisi data yang ingin Anda lihat:")
            kondisi = st.selectbox("Filter Kondisi:", ["Sesuai RUP", "Hanya di Realisasi", "Melebihi Pagu"])
            
            if kondisi == "Sesuai RUP":
                df_view = df_master[df_master['_merge'] == 'both']
            elif kondisi == "Hanya di Realisasi":
                df_view = df_master[df_master['_merge'] == 'right_only']
            else:
                df_view = df_master[(df_master['_merge'] == 'both') & (df_master['Anggaran_Realisasi'] > df_master[val_col])]
            
            st.dataframe(df_view, use_container_width=True)

        with t2:
            st.subheader("Rekapitulasi per Satuan Kerja (OPD)")
            if st.button("🚀 Proses Laporan OPD"):
                satkers = sorted(df_master['Satker_Final'].dropna().unique())
                rekap_rows = []

                for i, s in enumerate(satkers):
                    # Filter Data
                    ren_s = df_ren[df_ren['Nama Satuan Kerja'] == s]
                    real_s = df_real[df_real['Nama Satuan Kerja'] == s]
                    master_s = df_master[df_master['Satker_Final'] == s]

                    # 1. RUP SECTION
                    swa_r = ren_s[ren_s['Cara Pengadaan'].str.contains('Swakelola', case=False, na=False)]
                    pen_r = ren_s[ren_s['Cara Pengadaan'].str.contains('Penyedia', case=False, na=False)]

                    # 2. REALISASI SECTION
                    real_swa = real_s[real_s['Metode Pengadaan'].str.contains('Swakelola', case=False, na=False)]
                    
                    # Sesuai RUP (Match both)
                    match_s = master_s[master_s['_merge'] == 'both']
                    # Tidak Sesuai RUP (Hanya di realisasi)
                    unmatch_s = master_s[master_s['_merge'] == 'right_only']
                    # Toko Daring / Katalog 6.0
                    td_s = real_s[real_s['Metode Pengadaan'].str.contains('Tokodaring|E-Katalog 6.0', case=False, na=False)]

                    # HITUNG SELISIH
                    selisih_pkt = (pen_r['ID_RUP_CLEAN'].nunique() + swa_r['ID_RUP_CLEAN'].nunique()) - real_s['ID_RUP_CLEAN'].nunique()
                    selisih_ang = ren_s[val_col].sum() - real_s[val_col].sum()

                    # LOGIKA IDENTIFIKASI
                    if unmatch_s.shape[0] > 0:
                        identifikasi = "Jumlah Kode RUP di Realisasi Lebih Banyak dari Perencanaan"
                    elif selisih_ang < 0:
                        identifikasi = "Kemungkinan ada perubahan metode atau Overbudget"
                    else:
                        identifikasi = "Sesuai"

                    rekap_rows.append({
                        'No.': i + 1,
                        'OPD': s,
                        'RUP Swakelola (Paket)': swa_r.shape[0],
                        'RUP Swakelola (Anggaran)': swa_r[val_col].sum(),
                        'RUP Penyedia (Paket)': pen_r.shape[0],
                        'RUP Penyedia (Anggaran)': pen_r[val_col].sum(),
                        'Real Swakelola (Paket)': real_swa['ID_RUP_CLEAN'].nunique(),
                        'Real Swakelola (Anggaran)': real_swa[val_col].sum(),
                        'Real Sesuai RUP (Paket)': match_s.shape[0],
                        'Real Sesuai RUP (Anggaran)': match_s['Anggaran_Realisasi'].sum(),
                        'Real Tidak Sesuai RUP (Paket)': unmatch_s.shape[0],
                        'Real Tidak Sesuai RUP (Anggaran)': unmatch_s['Anggaran_Realisasi'].sum(),
                        'Toko Daring (Anggaran)': td_s[val_col].sum(),
                        'Selisih Paket': selisih_pkt,
                        'Selisih Anggaran': selisih_ang,
                        'Hasil Identifikasi': identifikasi
                    })

                df_rekap = pd.DataFrame(rekap_rows)

                # STYLING BARIS (HIJAU/MERAH)
                def color_rows(row):
                    if row['Hasil Identifikasi'] != "Sesuai":
                        return ['background-color: #ffcccc'] * len(row)
                    return ['background-color: #ccffcc'] * len(row)

                st.dataframe(df_rekap.style.apply(color_rows, axis=1), use_container_width=True)

                # DOWNLOAD
                out = io.BytesIO()
                df_rekap.to_excel(out, index=False)
                st.download_button("📥 Download Laporan Rekapitulasi", out.getvalue(), "Laporan_PBJ_Lampung.xlsx")

    else:
        st.error("Kolom 'Kode RUP' atau 'Total Nilai (Rp)' tidak ditemukan.")
else:
    st.info("Silakan unggah file SIRUP dan Realisasi untuk memulai audit.")
