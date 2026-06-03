import streamlit as st
import pandas as pd
import io

# ==============================================================================
# 1. KONFIGURASI HALAMAN & TEMA VISUAL
# ==============================================================================
st.set_page_config(page_title="Dashboard Rekonsiliasi PBJ", layout="wide", page_icon="📊")

st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 2rem; }
    .stat-card {
        background: linear-gradient(145deg, #ffffff, #f0f2f6);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.05);
        text-align: center;
        border-left: 5px solid #0c2461;
        margin-bottom: 1rem;
    }
    .stat-label { font-size: 15px; color: #555; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;}
    .stat-value-pkt { font-size: 24px; color: #0c2461; font-weight: 800; margin-top: 10px; }
    .stat-value-rp { font-size: 18px; color: #27ae60; font-weight: 700; }
    h2, h3 { color: #0c2461; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

if "data_proses" not in st.session_state:
    st.session_state.data_proses = None

# ==============================================================================
# 2. HEADER & SIDEBAR
# ==============================================================================
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("<h1>📊</h1>", unsafe_allow_html=True) 
with col_title:
    st.title("Sistem Rekonsiliasi SIRUP & Realisasi")
    st.markdown("Analisis Komprehensif Data Perencanaan vs Realisasi Anggaran")

with st.sidebar:
    st.header("📂 Unggah Berkas")
    st.info("Pastikan format berkas adalah CSV dari unduhan sistem resmi.")
    file_ren = st.file_uploader("1. Data Perencanaan (RUP)", type=['csv'])
    file_real = st.file_uploader("2. Data Realisasi", type=['csv'])
    tombol_proses = st.button("🔄 Proses Data Rekonsiliasi", use_container_width=True, type="primary")
    st.divider()

# ==============================================================================
# 3. LOGIKA PEMROSESAN DATA UTAMA
# ==============================================================================
if file_ren and file_real and tombol_proses:
    with st.spinner('Menyelaraskan data RUP dan Realisasi...'):
        df_ren = pd.read_csv(file_ren)
        df_real = pd.read_csv(file_real)
        
        # Kamus Pemetaan Kolom Pintar
        for df in [df_ren, df_real]:
            rename_dict = {}
            for col in df.columns:
                col_clean = str(col).strip().lower().replace('_', ' ').replace('.', '')
                if col_clean in ['total nilai', 'total nilai (rp)', 'pagu', 'nilai', 'pagu anggaran']:
                    rename_dict[col] = 'Total Nilai (Rp)'
                elif col_clean in ['kode rup', 'rup', 'id rup', 'kode_rup']:
                    rename_dict[col] = 'Kode RUP'
                elif col_clean in ['nama satuan kerja', 'satuan kerja', 'satker', 'nama satker', 'opd', 'nama opd']:
                    rename_dict[col] = 'Nama Satuan Kerja'
                elif col_clean in ['metode pengadaan', 'metode', 'metode_pengadaan']:
                    rename_dict[col] = 'Metode Pengadaan'
                elif col_clean in ['sumber transaksi', 'sumber', 'sumber_transaksi']:
                    rename_dict[col] = 'Sumber Transaksi'
                elif col_clean in ['cara pengadaan', 'cara', 'cara_pengadaan']:
                    rename_dict[col] = 'Cara Pengadaan'
                elif col_clean in ['nama penyedia', 'penyedia', 'rekanan', 'nama rekanan', 'nama_penyedia']:
                    rename_dict[col] = 'Nama Penyedia'
                elif col_clean in ['nama paket', 'paket', 'nama_paket', 'kegiatan']:
                    rename_dict[col] = 'Nama Paket'
            df.rename(columns=rename_dict, inplace=True)

        val_col = 'Total Nilai (Rp)'
        rup_col = 'Kode RUP'
        
        # Pembersihan Anggaran Angka
        for df in [df_ren, df_real]:
            if val_col in df.columns:
                if df[val_col].dtype == object:
                    df[val_col] = (df[val_col].astype(str)
                                   .str.replace('Rp', '', case=False, regex=False)
                                   .str.replace('.', '', regex=False)
                                   .str.replace(',', '.', regex=False)
                                   .str.strip())
                df[val_col] = pd.to_numeric(df[val_col], errors='coerce').fillna(0)

        # Standardisasi Kode RUP
        for df in [df_ren, df_real]:
            if rup_col in df.columns:
                df[rup_col] = df[rup_col].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

        # Pembersihan Teks Kolom Kritis
        for df in [df_ren, df_real]:
            for col in ['Metode Pengadaan', 'Sumber Transaksi', 'Cara Pengadaan', 'Nama Satuan Kerja', 'Nama Penyedia', 'Nama Paket']:
                if col in df.columns:
                    df[col] = df[col].fillna('').astype(str).str.strip()

        # Master RUP Perencanaan Bersih
        df_ren_clean = df_ren[df_ren[rup_col].str.lower() != 'nan'].drop_duplicates(subset=[rup_col])

        st.session_state.data_proses = {
            "df_ren": df_ren_clean, "df_real": df_real, "val_col": val_col, "rup_col": rup_col
        }
        st.success("Data berhasil diselaraskan menjadi dua blok terpisah!")

# ==============================================================================
# 4. PARSING DATA & DISTRIBUSI BLOK KIRI-KANAN (SINKRONISASI KOLOM PROTEKSI)
# ==============================================================================
if st.session_state.get("data_proses") is not None:
    dp = st.session_state["data_proses"]
    df_ren, df_real = dp["df_ren"], dp["df_real"]
    val_col, rup_col = dp["val_col"], dp["rup_col"]

    list_satker = ["Semua Satuan Kerja"] + sorted(df_ren['Nama Satuan Kerja'].dropna().unique())
    satker_terpilih = st.sidebar.selectbox("Tampilkan Data Unit Kerja:", list_satker)

    if satker_terpilih != "Semua Satuan Kerja":
        df_ren = df_ren[df_ren['Nama Satuan Kerja'] == satker_terpilih] if 'Nama Satuan Kerja' in df_ren.columns else df_ren
        df_real = df_real[df_real['Nama Satuan Kerja'] == satker_terpilih] if 'Nama Satuan Kerja' in df_real.columns else df_real

    df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False, case=False)]
    df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False, case=False)]

    # Pembuatan Ringkasan Atas (Agregat)
    agg_dict = {val_col: 'sum'}
    if 'Nama Penyedia' in df_real.columns:
        agg_dict['Nama Penyedia'] = lambda x: '; '.join(dict.fromkeys([str(s).strip() for s in x if str(s).strip().lower() not in ['', 'nan', 'none', '-']]))
    df_real_penyedia_sum = df_real_penyedia.groupby(rup_col, as_index=False).agg(agg_dict).rename(columns={val_col:'Anggaran_Realisasi'})
    df_sesuai = pd.merge(df_ren_penyedia.drop(columns=['Nama Penyedia'], errors='ignore'), df_real_penyedia_sum, on=rup_col, how='inner')

    # --- SINKRONISASI PENCEGAHAN KEYERROR ---
    df_sanding_raw = pd.merge(df_ren_penyedia, df_real_penyedia, on=rup_col, how='inner', suffixes=('_Rencana', '_Realisasi'))
    
    # Deteksi Dinamis (Gunakan Suffix jika bentrok, gunakan nama asli jika unik)
    col_satker_ren = 'Nama Satuan Kerja_Rencana' if 'Nama Satuan Kerja_Rencana' in df_sanding_raw.columns else 'Nama Satuan Kerja'
    col_paket_ren = 'Nama Paket_Rencana' if 'Nama Paket_Rencana' in df_sanding_raw.columns else 'Nama Paket'
    col_nilai_ren = 'Total Nilai (Rp)_Rencana' if 'Total Nilai (Rp)_Rencana' in df_sanding_raw.columns else 'Total Nilai (Rp)'
    
    col_penyedia_real = 'Nama Penyedia_Realisasi' if 'Nama Penyedia_Realisasi' in df_sanding_raw.columns else 'Nama Penyedia'
    col_nilai_real = 'Total Nilai (Rp)_Realisasi' if 'Total Nilai (Rp)_Realisasi' in df_sanding_raw.columns else 'Total Nilai (Rp)'
    col_sumber_real = 'Sumber Transaksi_Realisasi' if 'Sumber Transaksi_Realisasi' in df_sanding_raw.columns else 'Sumber Transaksi'
    col_metode_ren = 'Metode Pengadaan_Rencana' if 'Metode Pengadaan_Rencana' in df_sanding_raw.columns else 'Metode Pengadaan'

    # Langkah Aman Tambahan: Jika kolom absen total di file masukan, isi string kosong agar sistem tidak jebol
    for target_col in [col_satker_ren, col_paket_ren, col_nilai_ren, col_penyedia_real, col_nilai_real, col_sumber_real, col_metode_ren]:
        if target_col not in df_sanding_raw.columns:
            df_sanding_raw[target_col] = ""

    # Hitung Kalkulasi Selisih
    df_sanding_raw['Selisih Transaksi (Rp)'] = pd.to_numeric(df_sanding_raw[col_nilai_ren], errors='coerce').fillna(0) - pd.to_numeric(df_sanding_raw[col_nilai_real], errors='coerce').fillna(0)
    df_sanding_raw = df_sanding_raw.sort_values(by=[rup_col]).reset_index(drop=True)

    # 🛠️ MEMBUAT TABEL KIRI (BLOK PERENCANAAN) - Kebal Eror
    df_sanding_rencana = df_sanding_raw[[rup_col, col_satker_ren, col_paket_ren, col_nilai_ren]].rename(columns={
        col_satker_ren: 'Nama OPD',
        col_paket_ren: 'Nama Paket Perencanaan (SIRUP)',
        col_nilai_ren: 'Pagu Rencana (SIRUP)'
    })

    # 🛠️ MEMBUAT TABEL KANAN (BLOK REALISASI) - Kebal Eror
    df_sanding_realisasi = df_sanding_raw[[col_penyedia_real, col_nilai_real, 'Selisih Transaksi (Rp)', col_sumber_real, col_metode_ren]].rename(columns={
        col_penyedia_real: 'Nama Penyedia (Realisasi)',
        col_nilai_real: 'Nilai Riil Realisasi',
        col_sumber_real: 'Platform Realisasi',
        col_metode_ren: 'Metode Pemilihan'
    })

    # Kategori Lainnya (Parsial)
    df_real_only = df_real_penyedia[~df_real_penyedia[rup_col].isin(df_ren_penyedia[rup_col])]
    df_belum_teralisasi = df_ren_penyedia[~df_ren_penyedia[rup_col].isin(df_real_penyedia[rup_col])]
    df_ekatalog = df_real[df_real['Sumber Transaksi'].str.contains('e-katalog|katalog', na=False, case=False)]
    df_tokodaring = df_real[df_real['Sumber Transaksi'].str.contains('tokodaring', na=False, case=False)]

    def add_index(df):
        df_idx = df.copy()
        df_idx.insert(0, "No", range(1, len(df)+1))
        return df_idx

    # --- METRIK CARD ---
    st.markdown("---")
    st.subheader("Ringkasan Status Rekonsiliasi Anggaran")
    cols = st.columns(4)
    kategori_cards = [
        ("Sesuai RUP (Agregat)", df_sesuai, 'Anggaran_Realisasi'), 
        ("Hanya Realisasi", df_real_only, val_col), 
        ("Belum Terealisasi", df_belum_teralisasi, val_col), 
        ("E-Katalog 6.0", df_ekatalog, val_col)
    ]
    for idx, (label, df_cat, col_val) in enumerate(kategori_cards):
        pkt, ang = len(df_cat), df_cat[col_val].sum() if col_val in df_cat.columns else 0
        cols[idx].markdown(f"<div class='stat-card'><div class='stat-label'>{label}</div><div class='stat-value-pkt'>{pkt} Paket</div><div class='stat-value-rp'>Rp {ang:,.0f}</div></div>", unsafe_allow_html=True)

    # --- TAB INTERFACE DATA ---
    st.markdown("### Rincian Data per Kategori")
    tabs = st.tabs(["🔍 Detail Sanding RUP (2 Tabel Berjejer)", "✅ Sesuai RUP (Agregat)", "⚠️ Hanya Realisasi", "⏳ Belum Realisasi", "🛒 E-Katalog 6.0", "🏪 Toko Daring"])
    
    with tabs[0]:
        st.info("💡 Di bawah ini adalah dua tabel terpisah yang diletakkan berdampingan. Nomor urut (No) di sisi kiri dan kanan saling sinkron per baris transaksi.")
        col_screen_left, col_screen_space, col_screen_right = st.columns([1, 0.05, 1.2])
        with col_screen_left:
            st.markdown("#### 📋 1. Blok Perencanaan (SIRUP)")
            st.dataframe(add_index(df_sanding_rencana), use_container_width=True)
        with col_screen_right:
            st.markdown("#### 🚀 2. Blok Realisasi & Eksekusi")
            st.dataframe(add_index(df_sanding_realisasi), use_container_width=True)

    other_dfs = [df_sesuai, df_real_only, df_belum_teralisasi, df_ekatalog, df_tokodaring]
    for i, df_t in enumerate(other_dfs):
        with tabs[i+1]:
            st.dataframe(add_index(df_t), use_container_width=True)

# ==============================================================================
# 5. MODUL EXPORT EXCEL NATIVE SIDE-BY-SIDE
# ==============================================================================
    st.markdown("---")
    st.header("📥 Pusat Unduhan Laporan")
    
    dict_all_data = {
        "Sesuai_RUP_Agregat": df_sesuai,
        "Hanya_Realisasi": df_real_only,
        "Belum_Terealisasi": df_belum_teralisasi,
        "E-Katalog_6.0": df_ekatalog,
        "Toko_Daring": df_tokodaring
    }

    def generate_excel_side_by_side(dict_detail, df_left_src, df_right_src, satker):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            wb = writer.book
            title_fmt = wb.add_format({'bold': True, 'font_size': 14, 'font_name': 'Arial', 'color': '#0c2461'})
            section_fmt = wb.add_format({'bold': True, 'font_size': 11, 'font_name': 'Arial', 'color': '#2c3e50', 'bg_color': '#f1f2f6', 'border': 1})
            header_fmt = wb.add_format({'bold': True, 'bg_color': '#0c2461', 'color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
            curr_fmt = wb.add_format({'num_format': '#,##0', 'border': 1, 'valign': 'vcenter'})
            text_fmt = wb.add_format({'border': 1, 'valign': 'vcenter'})
            
            ws_s = wb.add_sheet("Sanding_Detail_Berjarak")
            ws_s.write('A1', 'LAPORAN REKONSILIASI DATA PBJ (SANDING SIDE-BY-SIDE)', title_fmt)
            ws_s.write('A2', f'Unit Kerja / Satker: {satker.upper()}')
            
            ws_s.merge_range('A4:E4', ' TABEL PERENCANAAN (DARI MASTER SIRUP)', section_fmt)
            ws_s.merge_range('H4:M4', ' TABEL EKSEKUSI REALISASI (DARI PLATFORM/KONTRAK)', section_fmt)
            
            df_xl_left = add_index(df_left_src)
            df_xl_right = add_index(df_right_src)
            
            df_xl_left.to_excel(writer, sheet_name="Sanding_Detail_Berjarak", index=False, startrow=4, startcol=0)
            df_xl_right.to_excel(writer, sheet_name="Sanding_Detail_Berjarak", index=False, startrow=4, startcol=7)
            
            for col_num, value in enumerate(df_xl_left.columns.values):
                ws_s.write(4, col_num, value, header_fmt)
                ws_s.set_column(col_num, col_num, 22 if col_num > 0 else 5)
            
            for col_num, value in enumerate(df_xl_right.columns.values):
                target_col = col_num + 7
                ws_s.write(4, target_col, value, header_fmt)
                ws_s.set_column(target_col, target_col, 22 if col_num > 0 else 5)
            
            ws_s.set_column(5, 5, 3)
            ws_s.set_column(6, 6, 3)
            
            for r_idx in range(len(df_xl_left)):
                excel_row = r_idx + 5
                for c_idx, col_name in enumerate(df_xl_left.columns):
                    val = df_xl_left.iloc[r_idx, c_idx]
                    if 'pagu' in str(col_name).lower() or 'nilai' in str(col_name).lower():
                        ws_s.write(excel_row, c_idx, pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0, curr_fmt)
                    else:
                        ws_s.write(excel_row, c_idx, str(val) if pd.notnull(val) else '', text_fmt)
                
                for c_idx, col_name in enumerate(df_xl_right.columns):
                    target_col = c_idx + 7
                    val = df_xl_right.iloc[r_idx, c_idx]
                    if any(k in str(col_name).lower() for k in ['nilai', 'pagu', 'selisih']):
                        ws_s.write(excel_row, target_col, pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0, curr_fmt)
                    else:
                        ws_s.write(excel_row, target_col, str(val) if pd.notnull(val) else '', text_fmt)

            for name, df_d in dict_detail.items():
                if len(df_d) > 0:
                    df_idx = add_index(df_d)
                    df_idx.to_excel(writer, sheet_name=name[:31], index=False)
                    ws_d = writer.sheets[name[:31]]
                    for col_num, value in enumerate(df_idx.columns.values):
                        ws_d.write(0, col_num, value, header_fmt)
                        ws_d.set_column(col_num, col_num, 24)
                    ws_d.set_column(0, 0, 6)
                    
                    for r_idx in range(len(df_idx)):
                        for c_idx, col_name in enumerate(df_idx.columns):
                            val = df_idx.iloc[r_idx, c_idx]
                            if any(k in str(col_name).lower() for k in ['nilai', 'pagu', 'anggaran', 'selisih']):
                                ws_d.write(r_idx+1, c_idx, pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0, curr_fmt)
                            else:
                                ws_d.write(r_idx+1, c_idx, str(val) if pd.notnull(val) else '', text_fmt)
        return out.getvalue()

    col_dl1, col_dl2 = st.columns([1, 1])
    with col_dl1:
        st.subheader("Laporan Keseluruhan (Buku)")
        master_excel = generate_excel_side_by_side(dict_all_data, df_sanding_rencana, df_sanding_realisasi, satker_terpilih)
        st.download_button(
            label="📁 UNDUH BUKU LAPORAN LENGKAP (Excel)",
            data=master_excel,
            file_name=f"Laporan_Rekonsiliasi_SideBySide_{satker_terpilih.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
        st.caption("*Lembar 'Sanding_Detail_Berjarak' berisi 2 tabel terpisah dengan batas kolom F & G kosong murni.*")
