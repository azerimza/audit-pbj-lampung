import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.express as px

# --- 1. CONFIG ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

# CSS untuk mempercantik tampilan kartu di sidebar
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 20px !important; font-family: 'Courier New', Courier, monospace; }
    .stMetric { border-bottom: 1px solid #ddd; padding-bottom: 10px; }
    h1 { color: #0c2461; }
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

# --- 2. SIDEBAR (LOGIKA & METRIK MENURUN) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=50)
    st.title("Admin Sistem")
    st.markdown(f"**Analis:** Reza Saputra Azmi")
    st.divider()
    
    file_ren = st.file_uploader("1. Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("2. Data Realisasi (CSV)", type=['csv'])

# --- 3. ENGINE & DASHBOARD ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()
    val_col = 'Total Nilai (Rp)'

    # Pembersihan Angka
    for d in [df_ren, df_real]:
        if val_col in d.columns:
            d[val_col] = pd.to_numeric(d[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # Hitung Total
    total_ren = df_ren[val_col].sum()
    total_real = df_real[val_col].sum()
    total_sisa = total_ren - total_real
    persen_serap = (total_real/total_ren*100) if total_ren > 0 else 0

    # TAMPILKAN METRIK MENURUN DI SIDEBAR
    with st.sidebar:
        st.divider()
        st.subheader("📊 Anggaran Detail")
        st.metric("Pagu Rencana", f"Rp {total_ren:,.0f}")
        st.metric("Realisasi Total", f"Rp {total_real:,.0f}", delta=f"{persen_serap:.2f}%")
        st.metric("Sisa Anggaran", f"Rp {total_sisa:,.0f}", 
                  delta="Overbudget" if total_sisa < 0 else "Sisa Pagu",
                  delta_color="normal" if total_sisa >= 0 else "inverse")

    # HALAMAN UTAMA
    st.markdown(f"# ⚖️ Dashboard Rekonsiliasi - Provinsi Lampung")
    
    tab1, tab2 = st.tabs(["📊 Statistik Visual", "📑 Tabel Rekapitulasi"])

    with tab1:
        c1, c2 = st.columns(2)
        
        # Grafik 1: Perbandingan Paket Menurun
        with c1:
            satkers = df_ren.groupby('Nama Satuan Kerja')[val_col].sum().sort_values(ascending=False).head(10).index
            df_plot = df_ren[df_ren['Nama Satuan Kerja'].isin(satkers)].copy()
            fig_bar = px.bar(df_plot.groupby('Nama Satuan Kerja')[val_col].sum().reset_index(), 
                             y='Nama Satuan Kerja', x=val_col, orientation='h',
                             title="Top 10 OPD Berdasarkan Pagu (Rp)", color_discrete_sequence=['#0c2461'])
            st.plotly_chart(fig_bar, use_container_width=True)

        # Grafik 2: Penyerapan Menurun
        with c2:
            fig_sisa = px.bar(df_ren.groupby('Nama Satuan Kerja')[val_col].sum().reset_index().head(10), 
                              x='Nama Satuan Kerja', y=val_col, title="Distribusi Anggaran per Bidang")
            st.plotly_chart(fig_sisa, use_container_width=True)

    with tab2:
        # Menampilkan tabel dengan angka yang jelas
        st.subheader("Detail Realisasi per Satuan Kerja")
        # Logika rekap sederhana untuk tabel
        rekap_opd = df_real.groupby('Nama Satuan Kerja')[val_col].sum().reset_index()
        rekap_opd = rekap_opd.rename(columns={val_col: 'Realisasi'})
        st.dataframe(rekap_opd.style.format({'Realisasi': 'Rp {:,.0f}'}), use_container_width=True)

else:
    st.info("Silakan unggah data di sidebar untuk melihat ringkasan anggaran.")
