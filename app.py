import streamlit as st
import pandas as pd
import io

# --- CONFIG ---
st.set_page_config(page_title="Dashboard Rekonsiliasi", layout="wide")

# --- LOGO & JUDUL ---
st.markdown("<div style='text-align:center;'><img src='LOGO_PEMPROV_BARU.png' width='200'></div>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center;'>Rekonsiliasi SIRUP & Realisasi</h2>", unsafe_allow_html=True)

# --- SIDEBAR CSV ---
with st.sidebar:
    st.markdown("## Upload Data CSV")
    file_ren = st.file_uploader("Upload Perencanaan (RUP)", type=['csv'])
    file_real = st.file_uploader("Upload Realisasi", type=['csv'])
    tombol_proses = st.button("Proses Data")
    st.divider()

if file_ren and file_real and tombol_proses:
    df_ren = pd.read_csv(file_ren)
    df_real = pd.read_csv(file_real)
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'

    # --- Bersihkan kolom & tipe ---
    for df in [df_ren, df_real]:
        df[rup_col] = df[rup_col].astype(str).str.strip()
        if 'Metode Pengadaan' in df.columns: df['Metode Pengadaan'] = df['Metode Pengadaan'].astype(str).str.lower()
        if 'Sumber Transaksi' in df.columns: df['Sumber Transaksi'] = df['Sumber Transaksi'].astype(str).str.lower().str.strip()
        if 'Cara Pengadaan' in df.columns: df['Cara Pengadaan'] = df['Cara Pengadaan'].astype(str).str.lower()
        if 'Nama Satuan Kerja' in df.columns: df['Nama Satuan Kerja'] = df['Nama Satuan Kerja'].astype(str).str.strip()
        df[val_col] = pd.to_numeric(df[val_col], errors='coerce').fillna(0)

    # --- Filter Satuan Kerja ---
    list_satker = ["Semua"] + sorted(df_ren['Nama Satuan Kerja'].dropna().unique())
    satker_terpilih = st.sidebar.selectbox("Pilih Satuan Kerja", list_satker)
    if satker_terpilih != "Semua":
        df_ren = df_ren[df_ren['Nama Satuan Kerja']==satker_terpilih]
        df_real = df_real[df_real['Nama Satuan Kerja']==satker_terpilih]

    # --- Hapus duplikasi RUP ---
    df_ren_unique = df_ren.drop_duplicates(subset=[rup_col])
    df_real_unique = df_real.drop_duplicates(subset=[rup_col])

    # --- Sesuai RUP ---
    df_real_sum = df_real_unique.groupby(rup_col, as_index=False)[val_col].sum()
    df_sesuai = pd.merge(df_ren_unique, df_real_sum, on=rup_col, how='inner')

    # --- Hanya Realisasi (exclude Swakelola) ---
    df_real_only = df_real[~df_real['Sumber Transaksi'].str.contains('swakelola', na=False) &
                           ~df_real[rup_col].isin(df_ren[rup_col])]
    jumlah_paket_real_only = df_real_only[rup_col].nunique()  # paket unik
    jumlah_anggaran_real_only = df_real_only[val_col].sum()   # anggaran semua baris

    # --- Belum Terealisasi ---
    df_belum = df_ren_unique[~df_ren_unique[rup_col].isin(df_real_unique[rup_col])]

    # --- Swakelola ---
    df_ren_swa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
    df_real_swa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]
    df_swakelola_tercatat = pd.merge(df_ren_swa, df_real_swa.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'}), on=rup_col, how='inner')
    df_swakelola_tidak_tercatat = df_ren_swa[~df_ren_swa[rup_col].isin(df_real_swa[rup_col])]

    # --- Toko Daring ---
    df_tokodaring = df_real[df_real['Sumber Transaksi'].str.contains('tokodaring', na=False)]

    # --- Fungsi bantu ---
    def hitung(df, val='Anggaran_Realisasi'):
        if val not in df.columns: val = val_col
        return len(df), df[val].sum() if val in df.columns else 0

    def add_index(df):
        df = df.copy()
        df.insert(0, "No", range(1, len(df)+1))
        return df

    # --- Ringkasan Rekonsiliasi ---
    st.markdown("## Ringkasan Rekonsiliasi")
    kategori = {
        "Sesuai RUP": df_sesuai,
        "Hanya Realisasi": df_real_only,
        "Belum Terealisasi": df_belum,
        "Swakelola Tercatat": df_swakelola_tercatat,
        "Swakelola Tidak Tercatat": df_swakelola_tidak_tercatat,
        "Toko Daring": df_tokodaring
    }

    for key, df_k in kategori.items():
        if key=="Hanya Realisasi":
            paket, anggaran = jumlah_paket_real_only, jumlah_anggaran_real_only
        else:
            paket, anggaran = hitung(df_k)
        st.markdown(f"**{key}:** {paket} Paket, Rp {anggaran:,.0f}")

    # --- Tabel Detail ---
    st.markdown("## Tabel Detail per Kategori")
    for key, df_k in kategori.items():
        st.markdown(f"### {key}")
        st.dataframe(add_index(df_k), use_container_width=True)

    # --- Download Excel ---
    st.markdown("## Unduh Laporan Excel")
    for key, df_k in kategori.items():
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            add_index(df_k).to_excel(writer, sheet_name=key[:31], index=False)
        st.download_button(f"Download {key}", data=buf.getvalue(), file_name=f"Laporan_{key}_{satker_terpilih}.xlsx", use_container_width=True)

else:
    st.info("Silakan unggah file Perencanaan dan Realisasi di sidebar dan klik tombol Proses Data.")
