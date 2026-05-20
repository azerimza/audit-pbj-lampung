import streamlit as st
import pandas as pd
import io

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Dashboard Analisa & Rekonsiliasi", layout="wide", page_icon="📊")
st.markdown("""
<style>
body { background-color: #f4f6f7; }
.stat-card { background-color: #ffffff; padding: 15px; border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; }
.stat-label { font-size: 14px; color: #555; font-weight: bold; }
.stat-value { font-size: 22px; color: #0c2461; font-weight: bold; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# --- LOGO DI TENGAH ---
st.markdown(
    "<div style='text-align: center;'><img src='LOGO_PEMPROV_BARU.png' width='200'></div>",
    unsafe_allow_html=True
)
st.markdown("<h2 style='text-align: center;'>📌 Dashboard Rekonsiliasi & Analisa Data</h2>", unsafe_allow_html=True)

# --- SIDEBAR CSV ---
with st.sidebar:
    st.markdown("## Upload Data CSV")
    file_ren = st.file_uploader("1. Upload Data Perencanaan (RUP)", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])

if file_ren and file_real:
    df_ren = pd.read_csv(file_ren)
    df_real = pd.read_csv(file_real)
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'

    # --- Bersihkan kolom & tipe ---
    for df in [df_ren, df_real]:
        df.columns = df.columns.str.strip()
        if 'Metode Pengadaan' in df.columns: df['Metode Pengadaan'] = df['Metode Pengadaan'].astype(str).str.lower()
        if 'Cara Pengadaan' in df.columns: df['Cara Pengadaan'] = df['Cara Pengadaan'].astype(str).str.lower()
        if 'Sumber Transaksi' in df.columns: df['Sumber Transaksi'] = df['Sumber Transaksi'].astype(str).str.lower()
        if 'Nama Satuan Kerja' in df.columns: df['Nama Satuan Kerja'] = df['Nama Satuan Kerja'].astype(str).str.strip()

    # --- Filter per Satuan Kerja ---
    list_satker = ["Semua"] + sorted(df_ren['Nama Satuan Kerja'].dropna().unique())
    satker_terpilih = st.sidebar.selectbox("Pilih Satuan Kerja", list_satker)
    if satker_terpilih != "Semua":
        def filter_satker(df): return df[df['Nama Satuan Kerja']==satker_terpilih] if 'Nama Satuan Kerja' in df.columns else df
        df_ren = filter_satker(df_ren)
        df_real = filter_satker(df_real)

    # =========================
    # REKONSILIASI
    # =========================
    # Sesuai RUP (Penyedia)
    df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_real_penyedia_sum = df_real_penyedia.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'})
    df_sesuai = pd.merge(df_ren_penyedia.drop_duplicates(subset=[rup_col]),
                         df_real_penyedia_sum, on=rup_col, how='inner')

    # Hanya Realisasi
    df_real_only = df_real[
        (~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)) &
        (~df_real['Sumber Transaksi'].str.contains('tokodaring', na=False))
    ]
    df_real_only = df_real_only[~df_real_only[rup_col].isin(df_ren[rup_col])]

    # Belum Terealisasi
    df_belum_teralisasi = df_ren[
        (~df_ren[rup_col].isin(df_real[rup_col])) &
        (df_ren['Cara Pengadaan'].str.contains('penyedia', case=False, na=False))
    ]

    # Swakelola
    df_ren_swa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
    df_real_swa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]
    df_swakelola_tercatat = pd.merge(
        df_ren_swa.drop_duplicates(subset=[rup_col]),
        df_real_swa.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'}),
        on=rup_col, how='inner'
    )
    df_swakelola_tidak_tercatat = df_ren_swa[~df_ren_swa[rup_col].isin(df_real_swa[rup_col])]

    # Toko Daring
    df_tokodaring = df_real[df_real['Sumber Transaksi'].str.contains('tokodaring', na=False)]

    # Hitung paket & anggaran
    def hitung(df, val='Anggaran_Realisasi'):
        if val not in df.columns: val = val_col
        return len(df), df[val].sum() if val in df.columns else 0

    jumlah_paket_sesuai, jumlah_anggaran_sesuai = hitung(df_sesuai)
    jumlah_paket_real_only, jumlah_anggaran_real_only = hitung(df_real_only)
    jumlah_paket_belum, jumlah_anggaran_belum = hitung(df_belum_teralisasi)
    jumlah_paket_swakelola_tercatat, jumlah_anggaran_swakelola_tercatat = hitung(df_swakelola_tercatat)
    jumlah_paket_swakelola_tidak_tercatat, jumlah_anggaran_swakelola_tidak_tercatat = hitung(df_swakelola_tidak_tercatat)
    jumlah_paket_tokodaring, jumlah_anggaran_tokodaring = hitung(df_tokodaring)

    # --- Tampilkan Ringkasan Rekonsiliasi ---
    st.markdown("## 📊 Ringkasan Rekonsiliasi")
    cols = st.columns([1.5,2,1.5,1.5,1.5,1.5])
    cols[0].markdown(f"<div class='stat-card'><div class='stat-label'>✅ Sesuai RUP</div><div class='stat-value'>{jumlah_paket_sesuai} Paket</div><div>Rp {jumlah_anggaran_sesuai:,.0f}</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='stat-card' style='border-top:5px solid #e67e22;'><div class='stat-label'>⚠️ Hanya Realisasi</div><div class='stat-value'>{jumlah_paket_real_only} Paket</div><div>Rp {jumlah_anggaran_real_only:,.0f}</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='stat-card' style='border-top:5px solid #f39c12;'><div class='stat-label'>⏳ Belum Terealisasi</div><div class='stat-value'>{jumlah_paket_belum} Paket</div><div>Rp {jumlah_anggaran_belum:,.0f}</div></div>", unsafe_allow_html=True)
    cols[3].markdown(f"<div class='stat-card' style='border-top:5px solid #27ae60;'><div class='stat-label'>🟢 Swakelola Tercatat</div><div class='stat-value'>{jumlah_paket_swakelola_tercatat} Paket</div><div>Rp {jumlah_anggaran_swakelola_tercatat:,.0f}</div></div>", unsafe_allow_html=True)
    cols[4].markdown(f"<div class='stat-card' style='border-top:5px solid #c0392b;'><div class='stat-label'>🔴 Swakelola Tidak Tercatat</div><div class='stat-value'>{jumlah_paket_swakelola_tidak_tercatat} Paket</div><div>Rp {jumlah_anggaran_swakelola_tidak_tercatat:,.0f}</div></div>", unsafe_allow_html=True)
    cols[5].markdown(f"<div class='stat-card' style='border-top:5px solid #9b59b6;'><div class='stat-label'>🛒 Toko Daring</div><div class='stat-value'>{jumlah_paket_tokodaring} Paket</div><div>Rp {jumlah_anggaran_tokodaring:,.0f}</div></div>", unsafe_allow_html=True)

    # =========================
    # Ringkasan Hasil Analisa Data.inaproc
    # =========================
    df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_ren_swakelola = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
    df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_real_swakelola = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]

    jml_paket_ren_penyedia = len(df_ren_penyedia)
    anggaran_ren_penyedia = df_ren_penyedia[val_col].sum()
    jml_paket_ren_swakelola = len(df_ren_swakelola)
    anggaran_ren_swakelola = df_ren_swakelola[val_col].sum()
    jml_paket_real_penyedia = len(df_real_penyedia)
    anggaran_real_penyedia = df_real_penyedia[val_col].sum()
    jml_paket_real_swakelola = len(df_real_swakelola)
    anggaran_real_swakelola = df_real_swakelola[val_col].sum()

    st.markdown("## 📌 Ringkasan Hasil Analisa (Data.inaproc)")
    cols = st.columns(4)
    cols[0].markdown(f"<div class='stat-card'><div class='stat-label'>Perencanaan Penyedia</div><div class='stat-value'>{jml_paket_ren_penyedia} Paket</div><div>Rp {anggaran_ren_penyedia:,.0f}</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='stat-card'><div class='stat-label'>Perencanaan Swakelola</div><div class='stat-value'>{jml_paket_ren_swakelola} Paket</div><div>Rp {anggaran_ren_swakelola:,.0f}</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='stat-card'><div class='stat-label'>Realisasi Penyedia</div><div class='stat-value'>{jml_paket_real_penyedia} Paket</div><div>Rp {anggaran_real_penyedia:,.0f}</div></div>", unsafe_allow_html=True)
    cols[3].markdown(f"<div class='stat-card'><div class='stat-label'>Realisasi Swakelola</div><div class='stat-value'>{jml_paket_real_swakelola} Paket</div><div>Rp {anggaran_real_swakelola:,.0f}</div></div>", unsafe_allow_html=True)

    # =========================
    # Download Excel Ringkasan
    # =========================
    st.markdown("## 🗂️ Download Excel Ringkasan")

    download_dict = {
        "Rekonsiliasi_Sesuai_RUP": df_sesuai,
        "Rekonsiliasi_Hanya_Realisasi": df_real_only,
        "Rekonsiliasi_Belum_Terealisasi": df_belum_teralisasi,
        "Rekonsiliasi_Swakelola_Tercatat": df_swakelola_tercatat,
        "Rekonsiliasi_Swakelola_Tidak_Tercatat": df_swakelola_tidak_tercatat,
        "Rekonsiliasi_Toko_Daring": df_tokodaring,
        "Analisa_Perencanaan_Penyedia": df_ren_penyedia,
        "Analisa_Perencanaan_Swakelola": df_ren_swakelola,
        "Analisa_Realisasi_Penyedia": df_real_penyedia,
        "Analisa_Realisasi_Swakelola": df_real_swakelola
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
