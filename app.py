import streamlit as st
import pandas as pd
import io

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Dashboard Rekonsiliasi", layout="wide")
st.markdown("""
<style>
body { background-color: #f4f6f7; }
.stat-card { background-color: #ffffff; padding: 15px; border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; }
.stat-label { font-size: 14px; color: #555; font-weight: bold; }
.stat-value { font-size: 22px; color: #0c2461; font-weight: bold; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. INISIALISASI SESSION STATE (Mencegah AttributeError Saat Pertama Kali Run)
# ==============================================================================
if "data_proses" not in st.session_state:
    st.session_state.data_proses = None

# --- LOGO & JUDUL ---
st.markdown("<div style='text-align:center;'><img src='LOGO_PEMPROV_BARU.png' width='200'></div>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center;'>Rekonsiliasi SIRUP & Realisasi</h2>", unsafe_allow_html=True)

# --- SIDEBAR CSV ---
with st.sidebar:
    st.markdown("## Upload Data CSV")
    file_ren = st.file_uploader("1. Upload Data Perencanaan (RUP)", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])
    tombol_proses = st.button("Proses Data", use_container_width=True)
    st.divider()

# ==============================================================================
# 2. PROSES DATA (Logika Penyaringan Pertama Kali)
# ==============================================================================
if file_ren and file_real and tombol_proses:
    df_ren = pd.read_csv(file_ren)
    df_real = pd.read_csv(file_real)
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'

    # --- Bersihkan kolom & tipe ---
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()
    for df in [df_ren, df_real]:
        if rup_col in df.columns: df[rup_col] = df[rup_col].astype(str).str.strip()
        if 'Metode Pengadaan' in df.columns: df['Metode Pengadaan'] = df['Metode Pengadaan'].astype(str).str.lower()
        if 'Sumber Transaksi' in df.columns: df['Sumber Transaksi'] = df['Sumber Transaksi'].astype(str).str.lower().str.strip()
        if 'Cara Pengadaan' in df.columns: df['Cara Pengadaan'] = df['Cara Pengadaan'].astype(str).str.lower()
        if 'Nama Satuan Kerja' in df.columns: df['Nama Satuan Kerja'] = df['Nama Satuan Kerja'].astype(str).str.strip()

    # --- HAPUS DUPLIKASI & JADI NUMERIC ---
    df_ren[val_col] = pd.to_numeric(df_ren[val_col], errors='coerce').fillna(0)
    df_real[val_col] = pd.to_numeric(df_real[val_col], errors='coerce').fillna(0)
    df_ren = df_ren.drop_duplicates(subset=[rup_col])
    df_real = df_real.drop_duplicates(subset=[rup_col])

    # Simpan ke session state agar tidak hilang saat filter sidebar berinteraksi
    st.session_state.data_proses = {
        "df_ren": df_ren,
        "df_real": df_real,
        "val_col": val_col,
        "rup_col": rup_col
    }

# ==============================================================================
# 3. BLOK UTAMA PERHITUNGAN & TAMPILAN DASHBOARD
# ==============================================================================
if st.session_state.get("data_proses") is not None:
    # Ambil basis data mentah yang aman dari session state
    dp = st.session_state["data_proses"]
    df_ren = dp["df_ren"]
    df_real = dp["df_real"]
    val_col = dp["val_col"]
    rup_col = dp["rup_col"]

    # --- FILTER SATUAN KERJA (Ditempatkan di luar pengondisian tombol agar persisten) ---
    list_satker = ["Semua"] + sorted(df_ren['Nama Satuan Kerja'].dropna().unique())
    satker_terpilih = st.sidebar.selectbox("Pilih Satuan Kerja", list_satker)

    # --- REKONSILIASI LOGIK ---
    df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_real_penyedia_sum = df_real_penyedia.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'})
    
    df_sesuai = pd.merge(df_ren_penyedia, df_real_penyedia_sum, on=rup_col, how='inner')
    df_real_only = df_real[~df_real[rup_col].isin(df_ren[rup_col])]
    df_belum_teralisasi = df_ren[~df_ren[rup_col].isin(df_real[rup_col])]

    df_ren_swa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
    df_real_swa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]
    
    df_swakelola_tercatat = pd.merge(df_ren_swa, df_real_swa.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'}), on=rup_col, how='inner')
    df_swakelola_tidak_tercatat = df_ren_swa[~df_ren_swa[rup_col].isin(df_real_swa[rup_col])]
    
    # Sesuai instruksi penyesuaian logika, pencarian dialihkan ke E-Katalog 6.0
    df_ekatalog = df_real[df_real['Sumber Transaksi'].str.contains('e-katalog|katalog', na=False)]
    df_tokodaring = df_real[df_real['Sumber Transaksi'].str.contains('tokodaring', na=False)]

    # --- PROSES FILTER SATKER ---
    if satker_terpilih != "Semua":
        def filter_satker(df): return df[df['Nama Satuan Kerja'] == satker_terpilih] if 'Nama Satuan Kerja' in df.columns else df
        df_sesuai = filter_satker(df_sesuai)
        df_real_only = filter_satker(df_real_only)
        df_belum_teralisasi = filter_satker(df_belum_teralisasi)
        df_swakelola_tercatat = filter_satker(df_swakelola_tercatat)
        df_swakelola_tidak_tercatat = filter_satker(df_swakelola_tidak_tercatat)
        df_ekatalog = filter_satker(df_ekatalog)
        df_tokodaring = filter_satker(df_tokodaring)

    # --- HITUNG & INDEX UTILITY ---
    def hitung(df, val='Anggaran_Realisasi'):
        if val not in df.columns: val = val_col
        return len(df), df[val].sum() if val in df.columns else 0

    def add_index(df):
        df = df.copy()
        df.insert(0, "No", range(1, len(df)+1))
        return df

    # --- Ringkasan Hasil Analisa (Data.inaproc) ---
    if satker_terpilih != "Semua":
        df_ren = filter_satker(df_ren)
        df_real = filter_satker(df_real)

    df_ren_penyedia_analisa = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_real_penyedia_analisa = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_ren_swakelola_analisa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
    df_real_swakelola_analisa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]

    jumlah_pkt_ren_penyedia, jumlah_ang_ren_penyedia = hitung(df_ren_penyedia_analisa, val_col)
    jumlah_pkt_real_penyedia, jumlah_ang_real_penyedia = hitung(df_real_penyedia_analisa, val_col)
    jumlah_pkt_ren_swakelola, jumlah_ang_ren_swakelola = hitung(df_ren_swakelola_analisa, val_col)
    jumlah_pkt_real_swakelola, jumlah_ang_real_swakelola = hitung(df_real_swakelola_analisa, val_col)

    st.markdown("## Ringkasan Hasil Analisa (Data.inaproc)")
    cols_a = st.columns(4)
    cols_a[0].markdown(f"<div class='stat-card'><div class='stat-label'>Penyedia (Rencana)</div><div class='stat-value'>{jumlah_pkt_ren_penyedia} Paket</div><div>Rp {jumlah_ang_ren_penyedia:,.0f}</div></div>", unsafe_allow_html=True)
    cols_a[1].markdown(f"<div class='stat-card'><div class='stat-label'>Penyedia (Realisasi)</div><div class='stat-value'>{jumlah_pkt_real_penyedia} Paket</div><div>Rp {jumlah_ang_real_penyedia:,.0f}</div></div>", unsafe_allow_html=True)
    cols_a[2].markdown(f"<div class='stat-card'><div class='stat-label'>Swakelola (Rencana)</div><div class='stat-value'>{jumlah_pkt_ren_swakelola} Paket</div><div>Rp {jumlah_ang_ren_swakelola:,.0f}</div></div>", unsafe_allow_html=True)
    cols_a[3].markdown(f"<div class='stat-card'><div class='stat-label'>Swakelola (Realisasi)</div><div class='stat-value'>{jumlah_pkt_real_swakelola} Paket</div><div>Rp {jumlah_ang_real_swakelola:,.0f}</div></div>", unsafe_allow_html=True)

    # --- Ringkasan Rekonsiliasi ---
    st.markdown("## Ringkasan Rekonsiliasi")
    jumlah_paket_sesuai, jumlah_anggaran_sesuai = hitung(df_sesuai, 'Anggaran_Realisasi')
    jumlah_paket_real_only, jumlah_anggaran_real_only = hitung(df_real_only, val_col)
    jumlah_paket_belum, jumlah_anggaran_belum = hitung(df_belum_teralisasi, val_col)
    jumlah_paket_swakelola_tercatat, jumlah_anggaran_swakelola_tercatat = hitung(df_swakelola_tercatat, 'Anggaran_Realisasi')
    jumlah_paket_swakelola_tidak_tercatat, jumlah_anggaran_swakelola_tidak_tercatat = hitung(df_swakelola_tidak_tercatat, val_col)
    jumlah_paket_ekatalog, jumlah_anggaran_ekatalog = hitung(df_ekatalog, val_col)

    cols_r = st.columns(6)
    cols_r[0].markdown(f"<div class='stat-card'><div class='stat-label'>Sesuai RUP</div><div class='stat-value'>{jumlah_paket_sesuai} Paket</div><div>Rp {jumlah_anggaran_sesuai:,.0f}</div></div>", unsafe_allow_html=True)
    cols_r[1].markdown(f"<div class='stat-card'><div class='stat-label'>Hanya Realisasi</div><div class='stat-value'>{jumlah_paket_real_only} Paket</div><div>Rp {jumlah_anggaran_real_only:,.0f}</div></div>", unsafe_allow_html=True)
    cols_r[2].markdown(f"<div class='stat-card'><div class='stat-label'>Belum Terealisasi</div><div class='stat-value'>{jumlah_paket_belum} Paket</div><div>Rp {jumlah_anggaran_belum:,.0f}</div></div>", unsafe_allow_html=True)
    cols_r[3].markdown(f"<div class='stat-card'><div class='stat-label'>Swakelola Tercatat</div><div class='stat-value'>{jumlah_paket_swakelola_tercatat} Paket</div><div>Rp {jumlah_anggaran_swakelola_tercatat:,.0f}</div></div>", unsafe_allow_html=True)
    cols_r[4].markdown(f"<div class='stat-card'><div class='stat-label'>Swakelola Tidak Tercatat</div><div class='stat-value'>{jumlah_paket_swakelola_tidak_tercatat} Paket</div><div>Rp {jumlah_anggaran_swakelola_tidak_tercatat:,.0f}</div></div>", unsafe_allow_html=True)
    cols_r[5].markdown(f"<div class='stat-card'><div class='stat-label'>E-Katalog 6.0</div><div class='stat-value'>{jumlah_paket_ekatalog} Paket</div><div>Rp {jumlah_anggaran_ekatalog:,.0f}</div></div>", unsafe_allow_html=True)

    # ==============================================================================
    # 4. TAMBAHAN: STRUKTUR FORMAT TABEL LAPORAN EKSEKUTIF (Sesuai Referensi)
    # ==============================================================================
    st.markdown("---")
    st.markdown("### 📋 Tabel Laporan Ringkasan Eksekutif")
    
    pagu_penyedia = df_ren_penyedia_analisa[val_col].sum()
    real_penyedia = df_sesuai['Anggaran_Realisasi'].sum()
    pagu_swa = df_ren_swakelola_analisa[val_col].sum()
    real_swa = df_swakelola_tercatat['Anggaran_Realisasi'].sum()

    data_laporan = {
        "Uraian / Jenis Pengadaan": ["Penyedia", "Swakelola", "TOTAL"],
        "Pagu Perencanaan (SIRUP)": [pagu_penyedia, pagu_swa, pagu_penyedia + pagu_swa],
        "Realisasi Tercatat": [real_penyedia, real_swa, real_penyedia + real_swa],
        "Selisih / Gap Anggaran": [pagu_penyedia - real_penyedia, pagu_swa - real_swa, (pagu_penyedia + pagu_swa) - (real_penyedia + real_swa)],
        "% Capaian Realisasi": [
            (real_penyedia / pagu_penyedia) if pagu_penyedia > 0 else 0,
            (real_swa / pagu_swa) if pagu_swa > 0 else 0,
            ((real_penyedia + real_swa) / (pagu_penyedia + pagu_swa)) if (pagu_penyedia + pagu_swa) > 0 else 0
        ]
    }
    df_lap_tampilan = pd.DataFrame(data_laporan)
    st.table(df_lap_tampilan.style.format({
        "Pagu Perencanaan (SIRUP)": "Rp {:,.0f}",
        "Realisasi Tercatat": "Rp {:,.0f}",
        "Selisih / Gap Anggaran": "Rp {:,.0f}",
        "% Capaian Realisasi": "{:.2%}"
    }))

    # --- Tabel Detail per Kategori ---
    st.markdown("## Tabel Detail per Kategori")
    tabs = ["Sesuai RUP", "Hanya Realisasi", "Belum Terealisasi", "Swakelola Tercatat", "Swakelola Tidak Tercatat", "E-Katalog 6.0", "Toko Daring"]
    dfs = [df_sesuai, df_real_only, df_belum_teralisasi, df_swakelola_tercatat, df_swakelola_tidak_tercatat, df_ekatalog, df_tokodaring]
    st_tabs = st.tabs(tabs)
    for tab, df_tab in zip(st_tabs, dfs):
        with tab:
            st.dataframe(add_index(df_tab), use_container_width=True)

    # ==============================================================================
    # 5. FORMAT ORIGINAL: DOWNLOADING DENGAN KUSTOMISASI DESAIN GOOGLE SHEETS
    # ==============================================================================
    st.markdown("## Unduh Laporan Excel")
    download_data = {
        "Perencanaan_Penyedia": df_ren_penyedia_analisa,
        "Perencanaan_Swakelola": df_ren_swakelola_analisa,
        "Realisasi_Penyedia": df_real_penyedia_analisa,
        "Realisasi_Swakelola": df_real_swakelola_analisa,
        "Sesuai_RUP": df_sesuai,
        "Hanya_Realisasi": df_real_only,
        "Belum_Terealisasi": df_belum_teralisasi,
        "Swakelola_Tercatat": df_swakelola_tercatat,
        "Swakelola_Tidak_Tercatat": df_swakelola_tidak_tercatat,
        "E_Katalog_6.0": df_ekatalog,
        "Toko_Daring": df_tokodaring
    }

    # Fungsi internal generator Excel terformat agar struktur file unduhan rapi dan memiliki ringkasan di awal sheet
    def generate_excel_file(df_summary, df_target, sheet_name_target, satker_name):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Formatter komponen tabel (Gaya Font & Garis Sel)
            title_fmt = workbook.add_format({'bold': True, 'font_size': 13, 'font_name': 'Arial'})
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#0c2461', 'color': 'white', 'border': 1, 'align': 'center', 'font_name': 'Arial'})
            currency_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1, 'font_name': 'Arial'})
            percent_fmt = workbook.add_format({'num_format': '0.00%', 'border': 1, 'font_name': 'Arial'})
            border_fmt = workbook.add_format({'border': 1, 'font_name': 'Arial'})

            # --- SHEET RINGKASAN UTAMA (Selalu muncul di awal file unduhan) ---
            df_summary.to_excel(writer, sheet_name="Ringkasan_Laporan", index=False, startrow=3)
            ws_sum = writer.sheets["Ringkasan_Laporan"]
            ws_sum.write('A1', f'LAPORAN RINGKASAN REKONSILIASI - {satker_name.upper()}', title_fmt)
            for c_idx, val in enumerate(df_summary.columns.values):
                ws_sum.write(3, c_idx, val, header_fmt)
                ws_sum.set_column(c_idx, c_idx, 25)
            for r_idx in range(len(df_summary)):
                row_pos = 4 + r_idx
                ws_sum.write(row_pos, 0, df_summary.iloc[r_idx, 0], border_fmt)
                ws_sum.write(row_pos, 1, df_summary.iloc[r_idx, 1], currency_fmt)
                ws_sum.write(row_pos, 2, df_summary.iloc[r_idx, 2], currency_fmt)
                ws_sum.write(row_pos, 3, df_summary.iloc[r_idx, 3], currency_fmt)
                ws_sum.write(row_pos, 4, df_summary.iloc[r_idx, 4], percent_fmt)

            # --- SHEET DATA DETAIL KATEGORI ---
            df_dl_indexed = add_index(df_target)
            df_dl_indexed.to_excel(writer, sheet_name=sheet_name_target[:31], index=False)
            ws_detail = writer.sheets[sheet_name_target[:31]]
            for c_idx, val in enumerate(df_dl_indexed.columns.values):
                ws_detail.write(0, c_idx, val, header_fmt)
            ws_detail.set_column(0, len(df_dl_indexed.columns), 18)

        return buf.getvalue()

    # Perulangan pembuatan tombol download terpisah sesuai format original kode Anda
    for name, df_dl in download_data.items():
        excel_binary = generate_excel_file(df_lap_tampilan, df_dl, name, satker_terpilih)
        st.download_button(
            label=f"Download Kategori {name.replace('_',' ')} (+ Ringkasan)",
            data=excel_binary,
            file_name=f"Laporan_{name}_{satker_terpilih.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

else:
    st.info("Silakan unggah file Perencanaan dan Realisasi di sidebar dan klik tombol Proses Data.")
