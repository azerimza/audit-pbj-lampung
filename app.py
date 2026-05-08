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

# --- 2. SIDEBAR (Tempat Variabel file_ren & file_real Dibuat) ---
with st.sidebar:
    # Header Logo & Nama
    col1, col2, col3 = st.columns([1, 2, 1]) 
    with col2:
        # Pastikan file gambar ini sudah di-upload ke GitHub Mas
        try:
            st.image("LOGO PEMPROV BARU.png", width=60)
        except:
            st.warning("Logo tidak ditemukan")
            
    st.markdown("<h3 style='text-align: center; margin-top: -10px;'>PEMBINAAN DAN ADVOKASI</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'><b>Reza Saputra Azmi</b></p>", unsafe_allow_html=True)
    st.divider()
    
    # --- INI ADALAH DEFINISI VARIABELNYA ---
    file_ren = st.file_uploader("1. Upload Data SIRUP", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])

# --- 3. LOGIKA PEMROSESAN (Hanya jalan jika file sudah di-upload) ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col, rup_col, satker_col = 'Total Nilai (Rp)', 'Kode RUP', 'Nama Satuan Kerja'
    
    # Bersihkan nama kolom
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    # FIX: Paksa Kode RUP jadi String untuk mencegah ValueError saat merge
    df_ren[rup_col] = df_ren[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)
    df_real[rup_col] = df_real[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)

    # Konversi Nilai Anggaran
    for df in [df_ren, df_real]:
        if val_col in df.columns:
            df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # PEMISAHAN KATEGORI
    def map_kat(m):
        m = str(m).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Tokodaring'
        if 'katalog 5' in m: return 'E-Katalog 5.0'
        if 'katalog 6' in m: return 'E-Katalog 6.0'
        if 'swakelola' in m: return 'Swakelola'
        return 'Lainnya'

    if 'Metode Pengadaan' in df_real.columns:
        df_real['Kat_Audit'] = df_real['Metode Pengadaan'].apply(map_kat)
    else:
        df_real['Kat_Audit'] = 'Lainnya'
    
    # AGREGASI KODE RUP (Menghindari Duplikasi Realisasi)
    df_real_agg = df_real.groupby(rup_col).agg({
        val_col: 'sum', satker_col: 'first', 'Kat_Audit': 'first', 'Jenis Pengadaan': 'first'
    }).reset_index()

    # --- 4. TAMPILAN UTAMA ---
    st.title("📊 Dashboard Audit & Rekonsiliasi")
    
    c1, c2, c3, c4 = st.columns(4)
    df_merge_glob = pd.merge(df_ren[[rup_col, val_col]], df_real_agg[[rup_col, val_col]], on=rup_col, how='right', indicator=True)
    
    c1.markdown(f'<div class="stat-card"><div class="stat-label">SESUAI RENCANA</div><div class="stat-value">{len(df_merge_glob[df_merge_glob["_merge"]=="both"])} Pkt</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-card"><div class="stat-label">TANPA RENCANA</div><div class="stat-value">{len(df_merge_glob[df_merge_glob["_merge"]=="right_only"])} Pkt</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-card"><div class="stat-label">TOTAL REALISASI</div><div class="stat-value">Rp {df_real[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-card"><div class="stat-label">EFISIENSI ANGGARAN</div><div class="stat-value">Rp {df_ren[val_col].sum() - df_real[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)

    # --- 5. TABEL LAPORAN ---
    st.divider()
    st.subheader("📑 Laporan Audit Rekonsiliasi Per Satker")
    
    rekap_list = []
    satker_list = sorted(df_ren[satker_col].dropna().unique())
    
    for i, s in enumerate(satker_list, 1):
        ren_s = df_ren[df_ren[satker_col] == s]
        real_s = df_real_agg[df_real_agg[satker_col] == s]
        merge_s = pd.merge(ren_s[[rup_col, val_col]], real_s[[rup_col, val_col, 'Kat_Audit']], on=rup_col, how='right', indicator=True)
        
        sw_ren = ren_s[ren_s['Jenis Pengadaan'].str.contains('Swakelola', na=False)]
        py_ren = ren_s[~ren_s['Jenis Pengadaan'].str.contains('Swakelola', na=False)]
        sesuai_rup_df = merge_s[merge_s['_merge'] == 'both']
        
        rekap_list.append({
            'No': i, 'Nama Satuan Kerja': s,
            'RUP Swakelola (Pkt)': len(sw_ren), 'RUP Swakelola (Angg)': sw_ren[val_col].sum(),
            'RUP Penyedia (Pkt)': len(py_ren), 'RUP Penyedia (Angg)': py_ren[val_col].sum(),
            'Real Swakelola (Angg)': real_s[real_s['Kat_Audit'] == 'Swakelola'][val_col].sum(),
            'Penyedia Sesuai RUP (Pkt)': len(sesuai_rup_df),
            'Penyedia Sesuai RUP (Angg)': sesuai_rup_df[val_col + '_y'].sum(),
            'Penyedia Tidak Sesuai (Angg)': merge_s[merge_s['_merge'] == 'right_only'][val_col + '_y'].sum(),
            'Selisih Paket': len(ren_s) - len(sesuai_rup_df),
            'Selisih Anggaran': ren_s[val_col].sum() - real_s[val_col].sum(),
            'Identifikasi': "Overbudget" if (sesuai_rup_df[val_col + '_y'] > sesuai_rup_df[val_col + '_x']).any() else "Normal"
        })

    df_final = pd.DataFrame(rekap_list)
    st.dataframe(df_final.style.format(precision=0, thousands=","), use_container_width=True)

    # --- 6. EXPORT ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, sheet_name='Laporan_Audit', index=False)
    st.download_button("📥 Download Laporan Lengkap", buffer.getvalue(), "Laporan_Audit_PBJ.xlsx")

else:
    st.info("👋 Selamat Datang! Silakan unggah data SIRUP dan Realisasi pada sidebar untuk memulai.")
