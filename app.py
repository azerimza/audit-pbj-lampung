import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- 1. KONFIGURASI ---
st.set_page_config(page_title="Audit PBJ Lampung", layout="wide")

st.markdown("""
    <style>
    .metric-card {
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 10px solid #0c2461; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-label { font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; }
    .metric-value { font-size: 28px; color: #0c2461; font-weight: bold; font-family: 'Consolas', monospace; }
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
    st.title("Audit PBJ v6.4")
    st.markdown("**Reza Saputra Azmi**")
    file_ren = st.file_uploader("1. Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("2. Data Realisasi (CSV)", type=['csv'])

# --- 3. CORE ENGINE ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col, rup_col, satker_col = 'Total Nilai (Rp)', 'Kode RUP', 'Nama Satuan Kerja'
    
    for df in [df_ren, df_real]:
        df.columns = df.columns.str.strip()
        df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # Grouping Realisasi per RUP (Poin 1 & 2)
    df_real_agg = df_real.groupby(rup_col).agg({
        val_col: 'sum', satker_col: 'first', 'Metode Pengadaan': 'first', 'Jenis Pengadaan': 'first'
    }).reset_index()

    # Identifikasi 7 Kategori (Poin 4)
    def map_kat(row):
        m = str(row['Metode Pengadaan']).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Toko Daring'
        if 'katalog 5' in m: return 'E-Katalog 5.0'
        if 'katalog 6' in m: return 'E-Katalog 6.0'
        if 'simpelpencatatan' in m: return 'SimpelPencatatan'
        if 'pencatatan' in m: return 'Pencatatan'
        if 'non tender' in m: return 'Non Tender'
        if 'swakelola' in m: return 'Swakelola'
        return 'Penyedia Lainnya'
    
    df_real_agg['Kategori'] = df_real_agg.apply(map_kat, axis=1)

    # --- 4. PEMBUATAN TABEL POIN 5 ---
    rekap_list = []
    all_satker = sorted(df_ren[satker_col].dropna().unique())

    for i, s in enumerate(all_satker, 1):
        # Data Rencana
        ren_s = df_ren[df_ren[satker_col] == s]
        swakelola_ren = ren_s[ren_s['Jenis Pengadaan'].str.contains('Swakelola', na=False)]
        penyedia_ren = ren_s[~ren_s['Jenis Pengadaan'].str.contains('Swakelola', na=False)]
        
        # Data Realisasi
        real_s = df_real_agg[df_real_agg[satker_col] == s]
        swakelola_real = real_s[real_s['Kategori'] == 'Swakelola']
        
        # Merge Per Satker untuk Sesuai/Tidak Sesuai RUP
        merge_s = pd.merge(ren_s[[rup_col, val_col]], real_s[[rup_col, val_col, 'Kategori']], on=rup_col, how='right', indicator=True)
        
        penyedia_sesuai = merge_s[(merge_s['_merge'] == 'both') & (merge_s['Kategori'] != 'Toko Daring')]
        penyedia_tidak_sesuai = merge_s[merge_s['_merge'] == 'right_only']
        penyedia_tokodaring = real_s[real_s['Kategori'] == 'Toko Daring']

        rekap_list.append({
            'No': i,
            'Nama Satuan Kerja': s,
            'RUP Swakelola (Pkt)': len(swakelola_ren),
            'RUP Swakelola (Angg)': swakelola_ren[val_col].sum(),
            'RUP Penyedia (Pkt)': len(penyedia_ren),
            'RUP Penyedia (Angg)': penyedia_ren[val_col].sum(),
            'Real Swakelola (Angg)': swakelola_real[val_col].sum(),
            'Penyedia Sesuai RUP (Angg)': penyedia_sesuai[val_col + '_y'].sum(),
            'Penyedia Tidak Sesuai RUP (Angg)': penyedia_tidak_sesuai[val_col + '_y'].sum(),
            'Penyedia Toko Daring (Angg)': penyedia_tokodaring[val_col].sum(),
            'Selisih Anggaran': ren_s[val_col].sum() - real_s[val_col].sum()
        })

    df_final = pd.DataFrame(rekap_list)

    # --- 5. TAMPILAN ---
    st.markdown(f"""<div class="metric-card"><div class="metric-label">TOTAL REALISASI</div><div class="metric-value">Rp {df_real[val_col].sum():,.0f}</div></div>""", unsafe_allow_html=True)

    st.subheader("📑 Laporan Audit Poin 5 (Rekap Satker)")
    st.dataframe(df_final.style.format(precision=0, thousands=","), use_container_width=True)

    # EXPORT EXCEL (Struktur Tabel Persis)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, sheet_name='Laporan_Audit', index=False)
    
    st.download_button("📥 Download Excel Laporan Poin 5", buffer.getvalue(), "Laporan_Audit_PBJ.xlsx")

else:
    st.info("Silakan unggah data untuk melihat laporan sesuai struktur Poin 5.")
