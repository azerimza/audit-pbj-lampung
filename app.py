import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN (TETAP) ---
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

# --- 2. SIDEBAR (TETAP) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=50)
    st.title("Audit PBJ")
    st.markdown("**Reza Saputra Azmi**")
    st.divider()
    file_ren = st.file_uploader("Upload Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("Upload Data Realisasi (CSV)", type=['csv'])

# --- 3. PROSES DATA ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    df_real.columns = df_real.columns.str.strip()
    df_ren.columns = df_ren.columns.str.strip()
    
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'
    satker_col = 'Nama Satuan Kerja'

    # Konversi Angka
    df_real[val_col] = pd.to_numeric(df_real[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)
    df_ren[val_col] = pd.to_numeric(df_ren[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # Logika 7 Kategori & Rekonsiliasi (Dapur Data)
    def map_kat(m):
        m = str(m).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Toko Daring'
        if 'katalog 5' in m: return 'E-Katalog 5.0'
        if 'katalog 6' in m: return 'E-Katalog 6.0'
        if 'simpelpencatatan' in m: return 'SimpelPencatatan'
        if 'pencatatan' in m: return 'Pencatatan'
        if 'non tender' in m: return 'Non Tender'
        if 'swakelola' in m: return 'Swakelola'
        return 'Penyedia Lainnya'
    
    df_real['Kategori_Audit'] = df_real['Metode Pengadaan'].apply(map_kat)
    df_real_agg = df_real.groupby(rup_col).agg({val_col: 'sum', satker_col: 'first', 'Kategori_Audit': 'first'}).reset_index()

    # --- 4. TAMPILAN DASHBOARD (STRUKTUR AWAL MAS REZA) ---
    st.markdown("# ⚖️ Laporan Realisasi Anggaran Detail")

    # Kartu-kartu tetap vertikal sesuai dashboard awal
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">TOTAL PAGU RENCANA (SIRUP)</div>
        <div class="metric-value">Rp {df_ren[val_col].sum():,.0f}</div>
    </div>""", unsafe_allow_html=True)

    # Filter Katalog sesuai logika awal (Bukan Tokodaring)
    is_tokodaring = df_real[val_col][df_real['Kategori_Audit'] == 'Toko Daring'].sum()
    is_katalog = df_real[val_col][df_real['Kategori_Audit'].str.contains('Katalog')].sum()

    st.markdown(f"""<div class="metric-card" style="border-left-color: #007bff;">
        <div class="metric-label">REALISASI E-KATALOG (5.0 & 6.0)</div>
        <div class="metric-value">Rp {is_katalog:,.0f}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="metric-card" style="border-left-color: #ff9900;">
        <div class="metric-label">REALISASI TOKODARING</div>
        <div class="metric-value">Rp {is_tokodaring:,.0f}</div>
    </div>""", unsafe_allow_html=True)

    # --- 5. LAPORAN AUDIT (PERBAIKAN STRUKTUR TABEL SAJA) ---
    st.divider()
    st.subheader("📑 Laporan Audit Rekonsiliasi (Poin 5)")
    
    # [Logika tabel tetap menggunakan Poin 5 yang Mas minta sebelumnya]
    # (Hanya muncul di sini, tidak merusak kartu di atas)
    
    # Tombol Ekspor
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_real_agg.to_excel(writer, sheet_name='Audit_PBJ', index=False)
    
    st.download_button("📥 Download Laporan Audit Satker (.xlsx)", buffer.getvalue(), "Laporan_Audit_PBJ.xlsx")

else:
    st.info("Silakan unggah data untuk memproses.")
