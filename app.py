import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime

# --- 1. CONFIG & STYLING (STYLE V6.1) ---
st.set_page_config(page_title="Audit Rekonsiliasi PBJ Lampung", layout="wide")

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
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=60)
    st.title("Audit PBJ v6.9")
    st.markdown("**Reza Saputra Azmi**")
    file_ren = st.file_uploader("Upload Data SIRUP", type=['csv'])
    file_real = st.file_uploader("Upload Data Realisasi", type=['csv'])

if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col, rup_col, satker_col = 'Total Nilai (Rp)', 'Kode RUP', 'Nama Satuan Kerja'
    
    for df in [df_ren, df_real]:
        df.columns = df.columns.str.strip()
        df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # POIN 4: Pemisahan Kategori
    def map_kat(m):
        m = str(m).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Tokodaring'
        if 'katalog 5' in m: return 'E-Katalog 5.0'
        if 'katalog 6' in m: return 'E-Katalog 6.0'
        if 'simpelpencatatan' in m: return 'SimpelPencatatan'
        if 'pencatatan' in m: return 'Pencatatan'
        if 'non tender' in m: return 'Non Tender'
        if 'swakelola' in m: return 'Swakelola'
        return 'Lainnya'

    df_real['Kat_Audit'] = df_real['Metode Pengadaan'].apply(map_kat)
    
    # POIN 1 & 2: Agregasi Kode RUP (Dijumlahkan dulu anggarannya)
    df_real_agg = df_real.groupby(rup_col).agg({
        val_col: 'sum', satker_col: 'first', 'Kat_Audit': 'first', 'Jenis Pengadaan': 'first'
    }).reset_index()

    # --- 3. DASHBOARD VISUAL (V6.1) ---
    st.title("📊 Dashboard Audit & Rekonsiliasi")
    
    c1, c2, c3, c4 = st.columns(4)
    df_merge_glob = pd.merge(df_ren[[rup_col, val_col]], df_real_agg[[rup_col, val_col]], on=rup_col, how='right', indicator=True)
    
    c1.markdown(f'<div class="stat-card"><div class="stat-label">SESUAI RENCANA</div><div class="stat-value">{len(df_merge_glob[df_merge_glob["_merge"]=="both"])}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-card"><div class="stat-label">TANPA RENCANA</div><div class="stat-value">{len(df_merge_glob[df_merge_glob["_merge"]=="right_only"])}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-card"><div class="stat-label">TOTAL REALISASI</div><div class="stat-value">Rp {df_real[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-card"><div class="stat-label">SISA ANGGARAN</div><div class="stat-value">Rp {df_ren[val_col].sum() - df_real[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)

    # Grafik Kategori
    df_chart = df_real_agg.groupby('Kat_Audit')[val_col].sum().reset_index()
    fig = px.bar(df_chart, x='Kat_Audit', y=val_col, color='Kat_Audit', title="Realisasi per Kategori")
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. LAPORAN POIN 5 (PENYEMPURNAAN TABEL) ---
    st.divider()
    st.subheader("📑 Laporan Audit Rekonsiliasi (Struktur Lengkap)")
    
    rekap_list = []
    for i, s in enumerate(sorted(df_ren[satker_col].dropna().unique()), 1):
        ren_s = df_ren[df_ren[satker_col] == s]
        real_s = df_real_agg[df_real_agg[satker_col] == s]
        merge_s = pd.merge(ren_s[[rup_col, val_col]], real_s[[rup_col, val_col, 'Kat_Audit']], on=rup_col, how='right', indicator=True)
        
        sw_ren = ren_s[ren_s['Jenis Pengadaan'].str.contains('Swakelola', na=False)]
        py_ren = ren_s[~ren_s['Jenis Pengadaan'].str.contains('Swakelola', na=False)]
        
        # Identifikasi Sesuai RUP (Both)
        sesuai_rup_df = merge_s[merge_s['_merge'] == 'both']
        over = sesuai_rup_df[sesuai_rup_df[val_col + '_y'] > sesuai_rup_df[val_col + '_x']]

        rekap_list.append({
            'No': i, 'Nama Satuan Kerja': s,
            'RUP Swakelola (Pkt)': len(sw_ren), 'RUP Swakelola (Angg)': sw_ren[val_col].sum(),
            'RUP Penyedia (Pkt)': len(py_ren), 'RUP Penyedia (Angg)': py_ren[val_col].sum(),
            'Real Swakelola (Angg)': real_s[real_s['Kat_Audit'] == 'Swakelola'][val_col].sum(),
            'Penyedia Sesuai RUP (Pkt)': len(sesuai_rup_df), # KOLOM BARU YANG DIMINTA
            'Penyedia Sesuai RUP (Angg)': sesuai_rup_df[val_col + '_y'].sum(),
            'Penyedia Tidak Sesuai (Angg)': merge_s[merge_s['_merge'] == 'right_only'][val_col + '_y'].sum(),
            'Penyedia Tokodaring (Angg)': real_s[real_s['Kat_Audit'] == 'Tokodaring'][val_col].sum(),
            'Selisih Anggaran': ren_s[val_col].sum() - real_s[val_col].sum(),
            'Identifikasi': f"Overbudget: {len(over)} pkt" if len(over) > 0 else "Normal"
        })

    df_final = pd.DataFrame(rekap_list)
    st.dataframe(df_final.style.format(precision=0, thousands=","), use_container_width=True)

    # EXPORT EXCEL
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, sheet_name='Laporan_Audit', index=False)
    st.download_button("📥 Download Excel Laporan Lengkap", buffer.getvalue(), "Laporan_Audit_PBJ_v6.9.xlsx")

else:
    st.info("Silakan unggah data untuk memproses.")
