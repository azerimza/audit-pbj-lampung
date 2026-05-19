import streamlit as st
import pandas as pd
import io

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Dashboard Rekonsiliasi", layout="wide", page_icon="📊")
st.markdown("""
<style>
body { background-color: #f4f6f7; }
.stat-card { background-color: #ffffff; padding: 15px; border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; }
.stat-label { font-size: 14px; color: #555; font-weight: bold; }
.stat-value { font-size: 22px; color: #0c2461; font-weight: bold; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# --- LOGO STATIS DI TENGAH ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.image("LOGO_PEMPROV_BARU.png", width=120)  # panggil logo langsung
    st.markdown("<h2 style='text-align: center;'>📌 Rekonsiliasi SIRUP & Realisasi</h2>", unsafe_allow_html=True)

# --- SIDEBAR CSV ---
with st.sidebar:
    st.markdown("## Upload Data CSV")
    file_ren = st.file_uploader("1. Upload Data Perencanaan (RUP)", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])
    st.divider()

if file_ren and file_real:
    df_ren = pd.read_csv(file_ren)
    df_real = pd.read_csv(file_real)
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'

    # Bersihkan kolom & tipe
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()
    for df in [df_ren, df_real]:
        if rup_col in df.columns: df[rup_col] = df[rup_col].astype(str).str.strip()
        if 'Metode Pengadaan' in df.columns: df['Metode Pengadaan'] = df['Metode Pengadaan'].astype(str).str.lower()
        if 'Sumber Transaksi' in df.columns: df['Sumber Transaksi'] = df['Sumber Transaksi'].astype(str).str.lower()
        if 'Cara Pengadaan' in df.columns: df['Cara Pengadaan'] = df['Cara Pengadaan'].astype(str).str.lower()
        if 'Nama Satuan Kerja' in df.columns: df['Nama Satuan Kerja'] = df['Nama Satuan Kerja'].astype(str).str.strip()

    # --- FILTER SATUAN KERJA ---
    list_satker = ["Semua"] + sorted(df_ren['Nama Satuan Kerja'].dropna().unique())
    satker_terpilih = st.sidebar.selectbox("Pilih Satuan Kerja", list_satker)

    # --- SESUAI RUP ---
    df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_ren.columns else df_ren.copy()
    df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_real.columns else df_real.copy()
    df_real_penyedia_sum = df_real_penyedia.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'})
    df_sesuai = pd.merge(df_ren_penyedia.drop_duplicates(subset=[rup_col]),
                         df_real_penyedia_sum, on=rup_col, how='inner') if not df_ren_penyedia.empty else pd.DataFrame(columns=[rup_col,'Anggaran_Realisasi'])

    # --- HANYA REALISASI ---
    df_real_only = df_real[(~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)) &
                            (~df_real['Sumber Transaksi'].str.contains('tokodaring', na=False))]
    if rup_col in df_ren.columns: df_real_only = df_real_only[~df_real_only[rup_col].isin(df_ren[rup_col])]

    # --- BELUM TEREALISASI (Hanya Penyedia) ---
    df_belum_teralisasi = df_ren[
        (~df_ren[rup_col].isin(df_real[rup_col])) &
        (df_ren['Cara Pengadaan'].str.contains('penyedia', case=False, na=False))
    ] if not df_ren.empty else pd.DataFrame()

    # --- SWAKELOLA ---
    df_ren_swa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
    df_real_swa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]
    df_swakelola_tercatat = pd.merge(df_ren_swa.drop_duplicates(subset=[rup_col]),
                                      df_real_swa.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'}),
                                      on=rup_col, how='inner')
    df_swakelola_tidak_tercatat = df_ren_swa[~df_ren_swa[rup_col].isin(df_real_swa[rup_col])]

    # --- TOKODARING ---
    df_tokodaring = df_real[df_real['Sumber Transaksi'].str.contains('tokodaring', na=False)]

    # --- FILTER PER SATUAN KERJA ---
    if satker_terpilih != "Semua":
        def filter_satker(df): return df[df['Nama Satuan Kerja']==satker_terpilih] if 'Nama Satuan Kerja' in df.columns else df
        df_sesuai = filter_satker(df_sesuai)
        df_real_only = filter_satker(df_real_only)
        df_belum_teralisasi = filter_satker(df_belum_teralisasi)
        df_swakelola_tercatat = filter_satker(df_swakelola_tercatat)
        df_swakelola_tidak_tercatat = filter_satker(df_swakelola_tidak_tercatat)
        df_tokodaring = filter_satker(df_tokodaring)

    # --- HITUNG PAKET & ANGGARAN ---
    def hitung(df, val='Anggaran_Realisasi'):
        if val not in df.columns: val = val_col
        return len(df), df[val].sum() if val in df.columns else 0

    jumlah_paket_sesuai, jumlah_anggaran_sesuai = hitung(df_sesuai)
    jumlah_paket_real_only, jumlah_anggaran_real_only = hitung(df_real_only)
    jumlah_paket_belum, jumlah_anggaran_belum = hitung(df_belum_teralisasi)
    jumlah_paket_swakelola_tercatat, jumlah_anggaran_swakelola_tercatat = hitung(df_swakelola_tercatat)
    jumlah_paket_swakelola_tidak_tercatat, jumlah_anggaran_swakelola_tidak_tercatat = hitung(df_swakelola_tidak_tercatat)
    jumlah_paket_tokodaring, jumlah_anggaran_tokodaring = hitung(df_tokodaring)

    # --- DASHBOARD METRIK FINAL ---
    st.markdown("## 📊 Ringkasan Rekonsiliasi")
    cols = st.columns([1.5,2,1.5,1.5,1.5,1.5])
    cols[0].markdown(f"<div class='stat-card'><div class='stat-label'>✅ Sesuai RUP</div><div class='stat-value'>{jumlah_paket_sesuai} Paket</div><div>Rp {jumlah_anggaran_sesuai:,.0f}</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='stat-card' style='border-top:5px solid #e67e22;'><div class='stat-label'>⚠️ Hanya Realisasi</div><div class='stat-value'>{jumlah_paket_real_only} Paket</div><div>Rp {jumlah_anggaran_real_only:,.0f}</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='stat-card' style='border-top:5px solid #f39c12;'><div class='stat-label'>⏳ Belum Terealisasi</div><div class='stat-value'>{jumlah_paket_belum} Paket</div><div>Rp {jumlah_anggaran_belum:,.0f}</div></div>", unsafe_allow_html=True)
    cols[3].markdown(f"<div class='stat-card' style='border-top:5px solid #27ae60;'><div class='stat-label'>🟢 Swakelola Tercatat</div><div class='stat-value'>{jumlah_paket_swakelola_tercatat} Paket</div><div>Rp {jumlah_anggaran_swakelola_tercatat:,.0f}</div></div>", unsafe_allow_html=True)
    cols[4].markdown(f"<div class='stat-card' style='border-top:5px solid #c0392b;'><div class='stat-label'>🔴 Swakelola Tidak Tercatat</div><div class='stat-value'>{jumlah_paket_swakelola_tidak_tercatat} Paket</div><div>Rp {jumlah_anggaran_swakelola_tidak_tercatat:,.0f}</div></div>", unsafe_allow_html=True)
    cols[5].markdown(f"<div class='stat-card' style='border-top:5px solid #9b59b6;'><div class='stat-label'>🛒 Toko Daring</div><div class='stat-value'>{jumlah_paket_tokodaring} Paket</div><div>Rp {jumlah_anggaran_tokodaring:,.0f}</div></div>", unsafe_allow_html=True)

    # --- TAB DETAIL PER KATEGORI ---
    st.markdown("## 📑 Tabel Detail per Kategori")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Sesuai RUP","Hanya Realisasi","Belum Terealisasi","Swakelola Tercatat","Swakelola Tidak Tercatat","Toko Daring"])
    with tab1: st.dataframe(df_sesuai,use_container_width=True)
    with tab2: st.dataframe(df_real_only,use_container_width=True)
    with tab3: st.dataframe(df_belum_teralisasi,use_container_width=True)
    with tab4: st.dataframe(df_swakelola_tercatat,use_container_width=True)
    with tab5: st.dataframe(df_swakelola_tidak_tercatat,use_container_width=True)
    with tab6: st.dataframe(df_tokodaring,use_container_width=True)

    # --- DOWNLOAD EXCEL SESUAI FILTER SATKER ---
    st.markdown("## 🗂️ Unduh Laporan Excel")
    download_data = {
        "Sesuai_RUP": df_sesuai,
        "Hanya_Realisasi": df_real_only,
        "Belum_Terealisasi": df_belum_teralisasi,
        "Swakelola_Tercatat": df_swakelola_tercatat,
        "Swakelola_Tidak_Tercatat": df_swakelola_tidak_tercatat,
        "Toko_Daring": df_tokodaring
    }
    for name, df_dl in download_data.items():
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df_dl.to_excel(writer, sheet_name=name, index=False)
        st.download_button(f"📥 Download {name}", data=buf.getvalue(), file_name=f"Laporan_{name}_{satker_terpilih.replace(' ','_')}.xlsx", use_container_width=True)

else:
    st.info("👋 Silakan unggah file Perencanaan dan Realisasi di sidebar.")
