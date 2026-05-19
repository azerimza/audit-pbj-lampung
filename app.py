import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Dashboard Rekonsiliasi", layout="wide", page_icon="📊")

st.markdown("""
<style>
body { background-color: #f4f6f7; }
.stat-card {
    background-color: #ffffff; 
    padding: 15px; 
    border-radius: 10px; 
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
    text-align: center; 
    margin-bottom: 20px;
}
.stat-label { font-size: 14px; color: #555; font-weight: bold; }
.stat-value { font-size: 22px; color: #0c2461; font-weight: bold; margin: 8px 0; }
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

# --- SIDEBAR ---
with st.sidebar:
    try:
        st.image("LOGO PEMPROV BARU.png", width=80)
    except:
        st.warning("Logo tidak ditemukan")
    st.markdown("## 📌 Rekonsiliasi SIRUP & Realisasi")
    file_ren = st.file_uploader("1. Upload Data SIRUP", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])
    st.divider()

# --- LOGIKA UTAMA ---
if file_ren and file_real:
    df_ren = read_csv_smart(file_ren)
    df_real = read_csv_smart(file_real)

    # Bersihkan kolom & tipe data
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'
    satker_col = 'Nama Satuan Kerja'

    for df in [df_ren, df_real]:
        if val_col in df.columns:
            df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D','', regex=True), errors='coerce').fillna(0)
        if rup_col in df.columns:
            df[rup_col] = df[rup_col].astype(str).str.strip().str.replace('.0','', regex=False)
        if satker_col in df.columns:
            df[satker_col] = df[satker_col].astype(str).str.strip()

    # Pilih OPD
    list_satker = ["Semua OPD"] + sorted(df_ren[satker_col].dropna().unique())
    satker_selected = st.selectbox("🔍 Pilih OPD:", list_satker)

    if satker_selected != "Semua OPD":
        df_ren = df_ren[df_ren[satker_col]==satker_selected]
        df_real = df_real[df_real[satker_col]==satker_selected]

    # Analisis dasar
    sesuai_rup = pd.merge(df_ren[[rup_col, val_col]], df_real[[rup_col, val_col]], on=rup_col, how='inner')
    tidak_teralisasi = df_ren[~df_ren[rup_col].isin(df_real[rup_col])]
    total_real = df_real[val_col].sum()

    # Tambahan: Tokodaring (misal dari kolom Metode Pengadaan)
    if 'Metode Pengadaan' in df_real.columns:
        df_tokodaring = df_real[df_real['Metode Pengadaan'].str.lower().str.contains('tokodaring', na=False)]
    else:
        df_tokodaring = pd.DataFrame(columns=df_real.columns)

    # --- DASHBOARD METRIK ---
    st.markdown("## 📊 Ringkasan Rekonsiliasi")
    c1, c2, c3 = st.columns([1.5, 2, 1.5])

    c1.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">✅ Sesuai RUP</div>
        <div class="stat-value">{len(sesuai_rup)} Paket</div>
        <div>Rp {sesuai_rup[val_col+'_x'].sum():,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

    c2.markdown(f"""
    <div class="stat-card" style="border-top: 5px solid #e67e22;">
        <div class="stat-label">⚠️ Tidak Terealisasi</div>
        <div class="stat-value">{len(tidak_teralisasi)} Paket</div>
        <div>Rp {tidak_teralisasi[val_col].sum():,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="stat-card" style="border-top: 5px solid #0c2461;">
        <div class="stat-label">💰 Total Realisasi</div>
        <div class="stat-value">Rp {total_real:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- VISUALISASI ---
    st.markdown("## 📈 Grafik Realisasi vs Rencana")
    df_plot = pd.merge(df_ren[[rup_col, val_col]], df_real[[rup_col, val_col]], on=rup_col, how='outer', suffixes=('_Rencana', '_Realisasi'))
    fig = px.bar(
        df_plot,
        x=rup_col,
        y=[val_col+'_Rencana', val_col+'_Realisasi'],
        barmode='group',
        title="Perbandingan Nilai RUP vs Realisasi",
        labels={val_col+'_Rencana':'Rencana', val_col+'_Realisasi':'Realisasi'}
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- TABEL DETAIL DENGAN TABS ---
    st.markdown("## 📑 Tabel Detail Rekonsiliasi")
    tab1, tab2, tab3 = st.tabs(["Semua RUP", "Tidak Terealisasi", "Tokodaring"])

    # Semua RUP
    df_all = pd.merge(df_ren, df_real, on=rup_col, how='outer', suffixes=('_Rencana','_Realisasi'))
    df_all_display = df_all.copy()
    if val_col+'_Rencana' in df_all_display.columns:
        df_all_display[val_col+'_Rencana'] = df_all_display[val_col+'_Rencana'].apply(lambda x: f"{x:,.0f}")
    if val_col+'_Realisasi' in df_all_display.columns:
        df_all_display[val_col+'_Realisasi'] = df_all_display[val_col+'_Realisasi'].apply(lambda x: f"{x:,.0f}")
    with tab1:
        st.dataframe(df_all_display, use_container_width=True)

    # Tidak Terealisasi
    df_tidak_display = tidak_teralisasi.copy()
    if val_col in df_tidak_display.columns:
        df_tidak_display[val_col] = df_tidak_display[val_col].apply(lambda x: f"{x:,.0f}")
    with tab2:
        st.dataframe(df_tidak_display, use_container_width=True)

    # Tokodaring
    df_td_display = df_tokodaring.copy()
    if val_col in df_td_display.columns:
        df_td_display[val_col] = df_td_display[val_col].apply(lambda x: f"{x:,.0f}")
    with tab3:
        st.dataframe(df_td_display, use_container_width=True)

    # --- DOWNLOAD EXCEL PER TAB ---
    st.markdown("## 🗂️ Unduh Laporan Excel")
    download_cols = ["Semua_RUP","Tidak_Terealisasi","Tokodaring"]
    download_dfs = [df_all_display, df_tidak_display, df_td_display]

    for name, df_dl in zip(download_cols, download_dfs):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df_dl.to_excel(writer, sheet_name=name, index=False)
        st.download_button(f"📥 Download {name}", data=buf.getvalue(), file_name=f"Laporan_{name}.xlsx", use_container_width=True)

else:
    st.info("👋 Silakan unggah file SIRUP dan Realisasi di sidebar.")
