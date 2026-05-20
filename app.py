import streamlit as st
import pandas as pd
import io

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Dashboard Analisa Data", layout="wide", page_icon="📊")
st.markdown("""
<style>
body { background-color: #f4f6f7; }
.stat-card { background-color: #ffffff; padding: 15px; border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; }
.stat-label { font-size: 14px; color: #555; font-weight: bold; }
.stat-value { font-size: 22px; color: #0c2461; font-weight: bold; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# --- LOGO TENGAH ---
st.markdown(
    "<div style='text-align: center;'><img src='LOGO_PEMPROV_BARU.png' width='200'></div>",
    unsafe_allow_html=True
)
st.markdown("<h2 style='text-align: center;'>📌 Ringkasan Hasil Analisa (Data.inaproc)</h2>", unsafe_allow_html=True)

# --- SIDEBAR CSV ---
with st.sidebar:
    st.markdown("## Upload Data CSV")
    file_ren = st.file_uploader("1. Upload Data Perencanaan (RUP)", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])

if file_ren and file_real:
    df_ren = pd.read_csv(file_ren)
    df_real = pd.read_csv(file_real)
    val_col = 'Total Nilai (Rp)'

    # Bersihkan kolom & tipe
    for df in [df_ren, df_real]:
        df.columns = df.columns.str.strip()
        if 'Metode Pengadaan' in df.columns: df['Metode Pengadaan'] = df['Metode Pengadaan'].astype(str).str.lower()
        if 'Cara Pengadaan' in df.columns: df['Cara Pengadaan'] = df['Cara Pengadaan'].astype(str).str.lower()
        if 'Sumber Transaksi' in df.columns: df['Sumber Transaksi'] = df['Sumber Transaksi'].astype(str).str.lower()
        if 'Nama Satuan Kerja' in df.columns: df['Nama Satuan Kerja'] = df['Nama Satuan Kerja'].astype(str).str.strip()

    # Filter Satuan Kerja
    list_satker = ["Semua"] + sorted(df_ren['Nama Satuan Kerja'].dropna().unique())
    satker_terpilih = st.sidebar.selectbox("Pilih Satuan Kerja", list_satker)

    if satker_terpilih != "Semua":
        def filter_satker(df): return df[df['Nama Satuan Kerja']==satker_terpilih] if 'Nama Satuan Kerja' in df.columns else df
        df_ren = filter_satker(df_ren)
        df_real = filter_satker(df_real)

    # --- Hitung Paket & Anggaran per Kategori ---
    df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_ren_swakelola = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
    df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_real_swakelola = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]

    # Paket dihitung semua baris
    jml_paket_ren_penyedia = len(df_ren_penyedia)
    anggaran_ren_penyedia = df_ren_penyedia[val_col].sum()
    jml_paket_ren_swakelola = len(df_ren_swakelola)
    anggaran_ren_swakelola = df_ren_swakelola[val_col].sum()
    jml_paket_real_penyedia = len(df_real_penyedia)
    anggaran_real_penyedia = df_real_penyedia[val_col].sum()
    jml_paket_real_swakelola = len(df_real_swakelola)
    anggaran_real_swakelola = df_real_swakelola[val_col].sum()

    # --- Tampilkan Ringkasan Kotak-Kotak ---
    st.markdown("## 📊 Ringkasan Hasil Analisa")
    cols = st.columns(4)
    cols[0].markdown(f"<div class='stat-card'><div class='stat-label'>Perencanaan Penyedia</div><div class='stat-value'>{jml_paket_ren_penyedia} Paket</div><div>Rp {anggaran_ren_penyedia:,.0f}</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='stat-card'><div class='stat-label'>Perencanaan Swakelola</div><div class='stat-value'>{jml_paket_ren_swakelola} Paket</div><div>Rp {anggaran_ren_swakelola:,.0f}</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='stat-card'><div class='stat-label'>Realisasi Penyedia</div><div class='stat-value'>{jml_paket_real_penyedia} Paket</div><div>Rp {anggaran_real_penyedia:,.0f}</div></div>", unsafe_allow_html=True)
    cols[3].markdown(f"<div class='stat-card'><div class='stat-label'>Realisasi Swakelola</div><div class='stat-value'>{jml_paket_real_swakelola} Paket</div><div>Rp {anggaran_real_swakelola:,.0f}</div></div>", unsafe_allow_html=True)

    # --- Tombol Download ---
    st.markdown("## 🗂️ Download Ringkasan Hasil Analisa")
    download_dict = {
        "Perencanaan_Penyedia": df_ren_penyedia,
        "Perencanaan_Swakelola": df_ren_swakelola,
        "Realisasi_Penyedia": df_real_penyedia,
        "Realisasi_Swakelola": df_real_swakelola
    }

    for name, df in download_dict.items():
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name=name)
        st.download_button(
            label=f"📥 Download {name}.xlsx",
            data=buf.getvalue(),
            file_name=f"{name}.xlsx",
            use_container_width=True
        )

else:
    st.info("👋 Silakan unggah file Perencanaan dan Realisasi di sidebar.")
