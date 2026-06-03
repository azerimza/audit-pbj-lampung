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
# 1. INISIALISASI SESSION STATE (Mencegah AttributeError sejak Awal Run)
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
# 2. PROSES LOGIKA DATA SAAT TOMBOL DIKLIK
# ==============================================================================
if file_ren and file_real and tombol_proses:
    with st.spinner("Sedang menyelaraskan data RUP dan Realisasi..."):
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

        # Simpan ke session state agar data persisten saat berinteraksi dengan filter/tombol
        st.session_state.data_proses = {
            "df_ren": df_ren,
            "df_real": df_real,
            "val_col": val_col,
            "rup_col": rup_col
        }

# ==============================================================================
# 3. KONDISIONAL TAMPILAN DASHBOARD & LAPORAN
# ==============================================================================
if st.session_state.get("data_proses") is not None:
    # Ekstrak data dari session state
    dp = st.session_state["data_proses"]
    df_ren = dp["df_ren"]
    df_real = dp["df_real"]
    val_col = dp["val_col"]
    rup_col = dp["rup_col"]

    # --- FILTER SATUAN KERJA (Diletakkan di luar tombol agar aman saat dipilih) ---
    list_satker = ["Semua"] + sorted(df_ren['Nama Satuan Kerja'].dropna().unique())
    satker_terpilih = st.sidebar.selectbox("Pilih Satuan Kerja", list_satker)

    # --- EKSEKUSI REKONSILIASI KATEGORI ---
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
    
    # Filter Transaksi Spesifik (E-Katalog 6.0 & Tokodaring)
    df_ekatalog = df_real[df_real['Sumber Transaksi'].str.contains('e-katalog|katalog', na=False)]
    df_tokodaring = df_real[df_real['Sumber Transaksi'].str.contains('tokodaring', na=False)]

    # --- APLIKASIKAN FILTER SATKER JIKA DIPILIH ---
    if satker_terpilih != "Semua":
        def filter_satker(df): 
            return df[df['Nama Satuan Kerja'] == satker_terpilih] if 'Nama Satuan Kerja' in df.columns else df
        
        df_ren = filter_satker(df_ren)
        df_real = filter_satker(df_real)
        df_sesuai = filter_satker(df_sesuai)
        df_real_only = filter_satker(df_real_only)
        df_belum_teralisasi = filter_satker(df_belum_teralisasi)
        df_swakelola_tercatat = filter_satker(df_swakelola_tercatat)
        df_swakelola_tidak_tercatat = filter_satker(df_swakelola_tidak_tercatat)
        df_ekatalog = filter_satker(df_ekatalog)
        df_tokodaring = filter_satker(df_tokodaring)

    # --- FUNGSI UTILITY (HITUNG & INDEX) ---
    def hitung(df, val='Anggaran_Realisasi'):
        if val not in df.columns: val = val_col
        return len(df), df[val].sum() if val in df.columns else 0

    def add_index(df):
        df = df.copy()
        df.insert(0, "No", range(1, len(df)+1))
        return df

    # --- RINGKASAN DATA INAPROC ---
    df_ren_penyedia_analisa = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_real_penyedia_analisa = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_ren_swakelola_analisa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
    df_real_swakelola_analisa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]

    st.markdown("## Ringkasan Hasil Analisa (Data.inaproc)")
    cols_a = st.columns(4)
    analisa_cards = [
        ("Penyedia (Rencana)", df_ren_penyedia_analisa, val_col),
        ("Penyedia (Realisasi)", df_real_penyedia_analisa, val_col),
        ("Swakelola (Rencana)", df_ren_swakelola_analisa, val_col),
        ("Swakelola (Realisasi)", df_real_swakelola_analisa, val_col)
    ]
    for idx, (lbl, df_c, c_col) in enumerate(analisa_cards):
        pkt, ang = hitung(df_c, c_col)
        cols_a[idx].markdown(f"<div class='stat-card'><div class='stat-label'>{lbl}</div><div class='stat-value'>{pkt} Paket</div><div>Rp {ang:,.0f}</div></div>", unsafe_allow_html=True)

    # --- RINGKASAN REKONSILIASI KANBAN ---
    st.markdown("## Ringkasan Rekonsiliasi")
    rec_categories = [
        ("Sesuai RUP", df_sesuai, 'Anggaran_Realisasi'),
        ("Hanya Realisasi", df_real_only, val_col),
        ("Belum Terealisasi", df_belum_teralisasi, val_col),
        ("Swakelola Tercatat", df_swakelola_tercatat, 'Anggaran_Realisasi'),
        ("Swakelola Sisa", df_swakelola_tidak_tercatat, val_col),
        ("E-Katalog 6.0", df_ekatalog, val_col)
    ]
    cols_r = st.columns(6)
    for idx, (label, df_cat, col_val) in enumerate(rec_categories):
        pkt, ang = hitung(df_cat, col_val)
        cols_r[idx].markdown(f"<div class='stat-card'><div class='stat-label'>{label}</div><div class='stat-value'>{pkt} Paket</div><div>Rp {ang:,.0f}</div></div>", unsafe_allow_html=True)

    # ==============================================================================
    # 4. TAMBAHAN BARU: TAMPILAN LAPORAN FORMAL (LAYOUT GOOGLE SHEETS)
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

    # --- TAB DETAIL PER KATEGORI ---
    st.markdown("## Tabel Detail per Kategori")
    tabs_names = [c[0] for c in rec_categories] + ["Toko Daring"]
    tabs_data = [c[1] for c in rec_categories] + [df_tokodaring]
    st_tabs = st.tabs(tabs_names)
    for tab, df_tab in zip(st_tabs, tabs_data):
        with tab:
            st.dataframe(add_index(df_tab), use_container_width=True)

    # ==============================================================================
    # 5. TAMBAHAN BARU: EKSPOR LAPORAN EXCEL YANG TERFORMAT (xlsxwriter)
    # ==============================================================================
    st.markdown("## Ekspor Dokumen Laporan")
    
    def generate_formatted_excel(df_summary, dict_details, satker_name):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Pengaturan Style Format Sel
            title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_name': 'Arial'})
            subtitle_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'font_name': 'Arial'})
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#0c2461', 'color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Arial'})
            currency_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1, 'font_name': 'Arial'})
            percent_fmt = workbook.add_format({'num_format': '0.00%', 'border': 1, 'font_name': 'Arial'})
            border_fmt = workbook.add_format({'border': 1, 'font_name': 'Arial'})
            bold_border_fmt = workbook.add_format({'bold': True, 'border': 1, 'font_name': 'Arial'})
            
            # --- SHEET 1: RINGKASAN LAPORAN UTAMA ---
            sheet_name = 'Laporan_Ringkasan'
            df_summary.to_excel(writer, sheet_name=sheet_name, index=False, startrow=4)
            worksheet = writer.sheets[sheet_name]
            
            # Menulis Judul Dokumen Atas
            worksheet.write('A1', 'LAPORAN REKONSILIASI PERENCANAAN DAN REALISASI ANGGARAN', title_fmt)
            worksheet.write('A2', f'SATUAN KERJA: {satker_name.upper()}', subtitle_fmt)
            
            # Mengaplikasikan format ke Header Tabel Summary
            for col_num, value in enumerate(df_summary.columns.values):
                worksheet.write(4, col_num, value, header_fmt)
                worksheet.set_column(col_num, col_num, 26)
            
            # Menerapkan Format Data di Tabel Utama
            for r_idx in range(len(df_summary)):
                row_excel = 5 + r_idx
                if r_idx == len(df_summary) - 1: # Row TOTAL (Baris Terakhir)
                    worksheet.write(row_excel, 0, df_summary.iloc[r_idx, 0], bold_border_fmt)
                    worksheet.write(row_excel, 1, df_summary.iloc[r_idx, 1], workbook.add_format({'bold':True, 'num_format':'#,##0', 'border':1}))
                    worksheet.write(row_excel, 2, df_summary.iloc[r_idx, 2], workbook.add_format({'bold':True, 'num_format':'#,##0', 'border':1}))
                    worksheet.write(row_excel, 3, df_summary.iloc[r_idx, 3], workbook.add_format({'bold':True, 'num_format':'#,##0', 'border':1}))
                    worksheet.write(row_excel, 4, df_summary.iloc[r_idx, 4], workbook.add_format({'bold':True, 'num_format':'0.00%', 'border':1}))
                else: # Baris reguler
                    worksheet.write(row_excel, 0, df_summary.iloc[r_idx, 0], border_fmt)
                    worksheet.write(row_excel, 1, df_summary.iloc[r_idx, 1], currency_fmt)
                    worksheet.write(row_excel, 2, df_summary.iloc[r_idx, 2], currency_fmt)
                    worksheet.write(row_excel, 3, df_summary.iloc[r_idx, 3], currency_fmt)
                    worksheet.write(row_excel, 4, df_summary.iloc[r_idx, 4], percent_fmt)

            # --- SHEET LAINNYA: DATA DETAIL UNTUK AUDIT ---
            for d_name, df_detail in dict_details.items():
                df_dl_indexed = add_index(df_detail)
                df_dl_indexed.to_excel(writer, sheet_name=d_name[:31], index=False)
                ws_detail = writer.sheets[d_name[:31]]
                
                # Format Header Detail
                for col_num, value in enumerate(df_dl_indexed.columns.values):
                    ws_detail.write(0, col_num, value, header_fmt)
                ws_detail.set_column(0, len(df_dl_indexed.columns), 20)
                
        return output.getvalue()

    # Gabungkan semua data detail ke dalam struktur dict
    download_sheets = {
        "Sesuai_RUP": df_sesuai,
        "Hanya_Realisasi": df_real_only,
        "Belum_Terealisasi": df_belum_teralisasi,
        "Swakelola_Tercatat": df_swakelola_tercatat,
        "Swakelola_Tidak_Tercatat": df_swakelola_tidak_tercatat,
        "E_Katalog_6.0": df_ekatalog,
        "Toko_Daring": df_tokodaring
    }
    
    # Jalankan pembuatan berkas terformat
    compiled_excel = generate_formatted_excel(df_lap_tampilan, download_sheets, satker_terpilih)
    
    st.download_button(
        label="📥 Unduh File Excel Resmi Terformat (Multi-Sheet)",
        data=compiled_excel,
        file_name=f"LAPORAN_REKONSILIASI_{satker_terpilih.replace(' ','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

else:
    st.info("Silakan unggah berkas Perencanaan (RUP) dan Realisasi di sidebar, kemudian klik 'Proses Data'.")
