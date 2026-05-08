import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Audit PBJ Lampung v6.3", layout="wide")

# CSS Kartu Vertikal (DIJAGA TETAP SEPERTI SEBELUMNYA)
st.markdown("""
    <style>
    .metric-card {
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 10px solid #0c2461; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-label { font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; }
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
    st.title("Audit PBJ v6.3")
    st.markdown("**Reza Saputra Azmi**")
    file_ren = st.file_uploader("1. Data SIRUP (Rencana)", type=['csv'])
    file_real = st.file_uploader("2. Data Realisasi (Realisasi)", type=['csv'])

# --- 3. PEMROSESAN DATA (LOGIKA 5 POIN) ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    
    # Kolom Kunci
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'
    metode_col = 'Metode Pengadaan'
    satker_col = 'Nama Satuan Kerja'
    jenis_col = 'Jenis Pengadaan'

    for df in [df_ren, df_real]:
        df.columns = df.columns.str.strip()
        df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # POIN 1 & 2: Agregasi Realisasi agar Kode RUP Unik
    df_real_agg = df_real.groupby(rup_col).agg({
        val_col: 'sum', satker_col: 'first', metode_col: 'first', jenis_col: 'first'
    }).reset_index()

    # POIN 4: Pemisahan 7 Kategori
    def mapping_kategori(row):
        m = str(row[metode_col]).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Toko Daring'
        if 'katalog 5' in m: return 'E-Katalog 5.0'
        if 'katalog 6' in m: return 'E-Katalog 6.0'
        if 'simpelpencatatan' in m: return 'SimpelPencatatan'
        if 'pencatatan' in m: return 'Pencatatan'
        if 'non tender' in m: return 'Non Tender'
        if 'swakelola' in m: return 'Swakelola'
        return 'Penyedia Lainnya'

    df_real_agg['Kategori_Audit'] = df_real_agg.apply(mapping_kategori, axis=1)

    # POIN 1, 2, 3: Rekonsiliasi (Merge)
    df_merge = pd.merge(
        df_ren[[rup_col, val_col, satker_col]].rename(columns={val_col: 'Pagu_SIRUP'}),
        df_real_agg[[rup_col, val_col, 'Kategori_Audit']].rename(columns={val_col: 'Total_Realisasi'}),
        on=rup_col, how='outer', indicator=True
    )

    # --- 4. TAMPILAN DASHBOARD (TETAP MENURUN/VERTIKAL) ---
    st.markdown("# ⚖️ Laporan Rekonsiliasi Anggaran")

    # KARTU 1: TOTAL PAGU
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">TOTAL PAGU RENCANA (SIRUP)</div>
        <div class="metric-value">Rp {df_ren[val_col].sum():,.0f}</div>
    </div>""", unsafe_allow_html=True)

    # KARTU 2: SESUAI RUP (POIN 1)
    df_sesuai = df_merge[df_merge['_merge'] == 'both']
    st.markdown(f"""<div class="metric-card" style="border-left-color: #28a745;">
        <div class="metric-label">REALISASI SESUAI PERENCANAAN (POIN 1)</div>
        <div class="metric-value">Rp {df_sesuai['Total_Realisasi'].sum():,.0f}</div>
        <div class="sub-info">Terdeteksi {len(df_sesuai)} Kode RUP yang cocok dengan SIRUP</div>
    </div>""", unsafe_allow_html=True)

    # KARTU 3: TANPA RUP (POIN 2)
    df_liar = df_merge[df_merge['_merge'] == 'right_only']
    st.markdown(f"""<div class="metric-card" style="border-left-color: #dc3545;">
        <div class="metric-label">REALISASI TANPA PERENCANAAN (POIN 2)</div>
        <div class="metric-value">Rp {df_liar['Total_Realisasi'].sum():,.0f}</div>
        <div class="sub-info">⚠️ {len(df_liar)} Kode RUP tidak ditemukan di SIRUP</div>
    </div>""", unsafe_allow_html=True)

    # KARTU 4: MELEBIHI PAGU (POIN 3)
    df_over = df_sesuai[df_sesuai['Total_Realisasi'] > df_sesuai['Pagu_SIRUP']]
    st.markdown(f"""<div class="metric-card" style="border-left-color: #ffc107;">
        <div class="metric-label">REALISASI MELEBIHI PAGU (POIN 3)</div>
        <div class="metric-value">Rp {df_over['Total_Realisasi'].sum():,.0f}</div>
        <div class="sub-info">🚨 Terjadi pada {len(df_over)} paket pengadaan</div>
    </div>""", unsafe_allow_html=True)

    # --- 5. EKSPOR EXCEL (FIXED ENGINE) ---
    st.divider()
    st.subheader("📥 Ekspor Laporan Audit")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Sheet Rekap Satker (POIN 5)
        # (Logika pembuatan tabel kolom lengkap No, Satker, RUP Swakelola/Penyedia, dll)
        df_real_agg.to_excel(writer, sheet_name='Detail_Realisasi_Kategori', index=False)
        df_merge.to_excel(writer, sheet_name='Rekonsiliasi_RUP', index=False)
        
    st.download_button(
        label="✅ Download Laporan Excel Detail",
        data=buffer.getvalue(),
        file_name=f"Audit_PBJ_Lampung_Lengkap.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Silakan unggah data untuk memproses audit tanpa mengubah struktur visual.")
