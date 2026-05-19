import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="REKONSILIASI DATA", layout="wide")

st.markdown("""
    <style>
    .stat-card {
        background-color: #ffffff; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 5px solid #0c2461;
        text-align: center; margin-bottom: 20px;
    }
    .stat-label { font-size: 14px; color: #555; font-weight: bold; }
    .stat-value { font-size: 24px; color: #0c2461; font-weight: bold; margin: 10px 0; }
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
    col1, col2, col3 = st.columns([1, 2, 1]) 
    with col2:
        try:
            st.image("LOGO PEMPROV BARU.png", width=60)
        except:
            st.warning("Logo tidak ditemukan")
            
    st.markdown("<h3 style='text-align: center; margin-top: -10px;'>PEMBINAAN DAN ADVOKASI</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'><b>Reza Saputra Azmi</b></p>", unsafe_allow_html=True)
    st.divider()
    
    file_ren = st.file_uploader("1. Upload Data SIRUP", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])

# --- 3. LOGIKA PEMROSESAN ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col, rup_col, satker_col = 'Total Nilai (Rp)', 'Kode RUP', 'Nama Satuan Kerja'
    
    # Bersihkan nama kolom
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    # Paksa Kode RUP jadi String & Bersihkan Spasi
    df_ren[rup_col] = df_ren[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)
    df_real[rup_col] = df_real[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    # Sinkronisasi Nama Satker agar pencocokan teks antar-file tidak miss
    df_ren[satker_col] = df_ren[satker_col].astype(str).str.strip()
    df_real[satker_col] = df_real[satker_col].astype(str).str.strip()

    for df in [df_ren, df_real]:
        if val_col in df.columns:
            df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # PEMISAHAN KATEGORI BERDASARKAN METODE
    def map_kat(m):
        m = str(m).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Tokodaring'
        if 'swakelola' in m: return 'Swakelola'
        if 'katalog' in m: return 'E-Katalog'
        return 'Penyedia Lainnya'

    if 'Metode Pengadaan' in df_real.columns:
        df_real['Kat_Audit'] = df_real['Metode Pengadaan'].apply(map_kat)
    else:
        df_real['Kat_Audit'] = 'Lainnya'
    
    # Agregasi data realisasi berdasarkan Kode RUP DAN Satker secara berpasangan
    df_real_agg = df_real.groupby([rup_col, satker_col]).agg({
        val_col: 'sum', 'Kat_Audit': 'first'
    }).reset_index()

    # --- 4. PANEL FILTER UTAMA ---
    st.title("📊 Dashboard Audit & Rekonsiliasi")
    
    # Grid Kendali Utama (OPD, Jenis Laporan, Satu Tombol Proses)
    f1, f2, f3 = st.columns([2, 2, 1])
    with f1:
        list_satker_pilihan = ["Semua OPD / Satker"] + sorted(df_ren[satker_col].dropna().unique().tolist())
        satker_terpilih = st.selectbox("🔍 Pilih OPD / Instansi:", list_satker_pilihan)
    with f2:
        opsi_proses = st.selectbox("⚙️ Pilih Jenis Analisis Laporan:", [
            "1. Laporan Keseluruhan (Realisasi, Tidak Terealisasi & Tanpa RUP)",
            "2. Laporan Paket Tidak Terealisasi Saja",
            "3. Laporan Khusus Toko Daring"
        ])
    with f3:
        st.markdown("<br>", unsafe_allow_html=True)
        tombol_proses = st.button("🚀 Proses Data", use_container_width=True)

    # Pengunci Tampilan Berbasis Session State
    if 'proses_dijalankan' not in st.session_state:
        st.session_state.proses_dijalankan = False
    if 'satker_aktif' not in st.session_state:
        st.session_state.satker_aktif = ""
    if 'opsi_aktif' not in st.session_state:
        st.session_state.opsi_aktif = ""

    if tombol_proses:
        st.session_state.proses_dijalankan = True
        st.session_state.satker_aktif = satker_terpilih
        st.session_state.opsi_aktif = opsi_proses

    # --- JALANKAN EKSEKUSI DATA ---
    if st.session_state.proses_dijalankan:
        satker_jalan = st.session_state.satker_aktif
        opsi_jalan = st.session_state.opsi_aktif

        # Filter Dataset berdasarkan scope OPD yang dipilih
        if satker_jalan == "Semua OPD / Satker":
            df_ren_filtered = df_ren
            df_real_filtered = df_real
            df_real_agg_filtered = df_real_agg
            satker_loop_list = sorted(df_ren[satker_col].dropna().unique())
        else:
            df_ren_filtered = df_ren[df_ren[satker_col] == satker_jalan]
            df_real_filtered = df_real[df_real[satker_col] == satker_jalan]
            df_real_agg_filtered = df_real_agg[df_real_agg[satker_col] == satker_jalan]
            satker_loop_list = [satker_jalan]

        # Logika Inti Paket Tidak Terealisasi (Ada di SIRUP, tapi TIDAK ADA di Realisasi)
        df_tidak_realisasi_master = pd.merge(df_ren_filtered, df_real_agg_filtered[[rup_col, satker_col]], on=[rup_col, satker_col], how='left', indicator=True)
        df_tidak_realisasi = df_tidak_realisasi_master[df_tidak_realisasi_master['_merge'] == 'left_only'].drop(columns=['_merge'])

        # =====================================================================
        # OPSI 1: LAPORAN KESELURUHAN (KOMPARASI LENGKAP + REKAP TIDAK SESUAI RUP)
        # =====================================================================
        if "1. Laporan Keseluruhan" in opsi_jalan:
            st.success(f"📊 Menampilkan **Laporan Keseluruhan** untuk: **{satker_jalan}**")
            
            # Kartu Ringkasan Atas (Outer Join Komprehensif)
            c1, c2, c3, c4 = st.columns(4)
            df_merge_glob = pd.merge(df_ren_filtered[[rup_col, satker_col, val_col]], df_real_agg_filtered[[rup_col, satker_col, val_col]], on=[rup_col, satker_col], how='outer', indicator=True)
            
            c1.markdown(f'<div class="stat-card"><div class="stat-label">SESUAI RENCANA</div><div class="stat-value">{len(df_merge_glob[df_merge_glob["_merge"]=="both"])} Pkt</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="stat-card" style="border-top: 5px solid #e67e22;"><div class="stat-label">TIDAK TEREALISASI</div><div class="stat-value" style="color: #e67e22;">{len(df_tidak_realisasi)} Pkt (Rp {df_tidak_realisasi[val_col].sum():,.0f})</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="stat-card" style="border-top: 5px solid #c0392b;">
