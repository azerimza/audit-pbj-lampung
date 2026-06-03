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
        
        # Pembersihan Anggaran
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

        # Master RUP Bersih
        df_ren_clean = df_ren[df_ren[rup_col].str.lower() != 'nan'].drop_duplicates(subset=[rup_col])

        st.session_state.data_proses = {
            "df_ren": df_ren_clean, "df_real": df_real, "val_col": val_col, "rup_col": rup_col
        }
        st.success("Data berhasil diproses dengan pemisah visual antar blok!")

# ==============================================================================
# 4. RENDER DASHBOARD & INJEKSI KOLOM JARAK (SPACER CORNER)
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
    df_ren_swa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False, case=False)]
    df_real_swa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False, case=False)]

    # Perhitungan Agregat untuk Ringkasan Atas
    agg_dict = {val_col: 'sum'}
    if 'Nama Penyedia' in df_real.columns:
        agg_dict['Nama Penyedia'] = lambda x: '; '.join(dict.fromkeys([str(s).strip() for s in x if str(s).strip().lower() not in ['', 'nan', 'none', '-']]))
    df_real_penyedia_sum = df_real_penyedia.groupby(rup_col, as_index=False).agg(agg_dict).rename(columns={val_col:'Anggaran_Realisasi'})
    df_sesuai = pd.merge(df_ren_penyedia.drop(columns=['Nama Penyedia'], errors='ignore'), df_real_penyedia_sum, on=rup_col, how='inner')

    # --- 🛠️ PROSES DATA SANDING DENGAN 2 KOLOM KOSONG (SPACER) ---
    df_sanding_raw = pd.merge(df_ren_penyedia, df_real_penyedia, on=rup_col, how='inner', suffixes=('_Rencana', '_Realisasi'))
    df_sanding_raw['Selisih Transaksi (Rp)'] = df_sanding_raw['Total Nilai (Rp)_Rencana'] - df_sanding_raw['Total Nilai (Rp)_Realisasi']

    # 1. Mengubah nama kolom ke bentuk Laporan Resmi terlebih dahulu
    mapping_nama_kolom = {
        'Nama Satuan Kerja_Rencana': 'Nama OPD',
        'Nama Paket_Rencana': 'Nama Paket Perencanaan (SIRUP)',
        'Total Nilai (Rp)_Rencana': 'Pagu Rencana (SIRUP)',
        'Nama Penyedia_Realisasi': 'Nama Penyedia (Realisasi)',
        'Total Nilai (Rp)_Realisasi': 'Nilai Riil Realisasi',
        'Sumber Transaksi_Realisasi': 'Platform Realisasi',
        'Metode Pengadaan_Rencana': 'Metode Pemilihan'
    }
    df_sanding_ready = df_sanding_raw.rename(columns=mapping_nama_kolom)

    # 2. Injeksi 2 Kolom Kosong Unik (Menggunakan Karakter Spasi Berbeda)
    df_sanding_ready[' '] = ''   # Spasi 1 (Kolom Kosong Pertama)
    df_sanding_ready['  '] = ''  # Spasi 2 (Kolom Kosong Kedua)

    # 3. Penyusunan Formasi: KIRI -> JARAK -> KANAN
    kolom_sanding_final = [
        rup_col,
        'Nama OPD',
        'Nama Paket Perencanaan (SIRUP)',
        'Pagu Rencana (SIRUP)',
        ' ',   # Pembatas 1
        '  ',  # Pembatas 2
        'Nama Penyedia (Realisasi)',
        'Nilai Riil Realisasi',
        'Selisih Transaksi (Rp)',
        'Platform Realisasi',
        'Metode Pemilihan'
    ]
    
    kolom_ada = [c for c in kolom_sanding_final if c in df_sanding_ready.columns]
    kolom_sisa = [c for c in df_sanding_ready.columns if c not in kolom_ada]
    df_sanding_view = df_sanding_ready[kolom_ada + kolom_sisa].sort_values(by=[rup_col]).reset_index(drop=True)

    # Kategori Lainnya
    df_real_only = df_real_penyedia[~df_real_penyedia[rup_col].isin(df_ren_penyedia[rup_col])]
    df_belum_teralisasi = df_ren_penyedia[~df_ren_penyedia[rup_col].isin(df_real_penyedia[rup_col])]
    df_swakelola_tercatat = pd.merge(df_ren_swa, df_real_swa.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'}), on=rup_col, how='inner')
    df_ekatalog = df_real[df_real['Sumber Transaksi'].str.contains('e-katalog|katalog', na=False, case=False)]
    df_tokodaring = df_real[df_real['Sumber Transaksi'].str.contains('tokodaring', na=False, case=False)]

    def hitung(df, col): return len(df), df[col].sum() if col in df.columns else 0
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
        pkt, ang = hitung(df_cat, col_val)
        cols[idx].markdown(f"""
        <div class='stat-card'>
            <div class='stat-label'>{label}</div>
            <div class='stat-value-pkt'>{pkt} Paket</div>
            <div class='stat-value-rp'>Rp {ang:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    # --- LAPORAN EKSEKUTIF ---
    st.markdown("---")
    st.subheader("📋 Laporan Ringkasan Eksekutif")
    pagu_penyedia = df_ren_penyedia[val_col].sum()
    real_penyedia = df_sesuai['Anggaran_Realisasi'].sum()
    pagu_swa = df_ren_swa[val_col].sum()
    real_swa = df_swakelola_tercatat['Anggaran_Realisasi'].sum()

    df_laporan = pd.DataFrame({
        "Jenis Pengadaan": ["Penyedia", "Swakelola", "TOTAL KESELURUHAN"],
        "Pagu Perencanaan (SIRUP)": [pagu_penyedia, pagu_swa, pagu_penyedia + pagu_swa],
        "Realisasi Tercatat": [real_penyedia, real_swa, real_penyedia + real_swa],
        "Gap (Selisih)": [pagu_penyedia - real_penyedia, pagu_swa - real_swa, (pagu_penyedia + pagu_swa) - (real_penyedia + real_swa)],
        "Capaian (%)": [(real_penyedia / pagu_penyedia) if pagu_penyedia > 0 else 0, (real_swa / pagu_swa) if pagu_swa > 0 else 0, ((real_penyedia + real_swa) / (pagu_penyedia + pagu_swa)) if (pagu_penyedia + pagu_swa) > 0 else 0]
    })
    st.table(df_laporan.style.format({"Pagu Perencanaan (SIRUP)": "Rp {:,.0f}", "Realisasi Tercatat": "Rp {:,.0f}", "Gap (Selisih)": "Rp {:,.0f}", "Capaian (%)": "{:.2%}"}))

    # --- TAB PREVIEW DATA STREAMLIT ---
    st.markdown("### Rincian Data per Kategori")
    tab_titles = ["🔍 Detail Sanding RUP (Berjarak)", "✅ Sesuai RUP (Agregat)", "⚠️ Hanya Realisasi", "⏳ Belum Realisasi", "🛒 E-Katalog 6.0", "🏪 Toko Daring"]
    tab_dfs = [df_sanding_view, df_sesuai, df_real_only, df_belum_teralisasi, df_ekatalog, df_tokodaring]
    
    tabs = st.tabs(tab_titles)
    for tab, df_tab in zip(tabs, tab_dfs):
        with tab:
            st.dataframe(add_index(df_tab), use_container_width=True)

# ==============================================================================
# 5. MODUL EXPORT EXCEL DENGAN STRUKTUR PINTAR (WARNA & BORDER KOSONG PADA JARAK)
# ==============================================================================
    st.markdown("---")
    st.header("📥 Pusat Unduhan Laporan")
    
    dict_all_data = {
        "Sanding_Detail_Berjarak": df_sanding_view,
        "Sesuai_RUP_Agregat": df_sesuai,
        "Hanya_Realisasi": df_real_only,
        "Belum_Terealisasi": df_belum_teralisasi,
        "E-Katalog_6.0": df_ekatalog,
        "Toko_Daring": df_tokodaring
    }

    def generate_excel_with_gap(df_sum, dict_detail, satker):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            wb = writer.book
            title_fmt = wb.add_format({'bold': True, 'font_size': 14, 'font_name': 'Arial'})
            
            # Format Standar Header & Sel Aktif
            header_fmt = wb.add_format({'bold': True, 'bg_color': '#0c2461', 'color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
            curr_fmt = wb.add_format({'num_format': '#,##0', 'border': 1, 'valign': 'vcenter'})
            pct_fmt = wb.add_format({'num_format': '0.00%', 'border': 1, 'valign': 'vcenter'})
            text_fmt = wb.add_format({'border': 1, 'valign': 'vcenter'})
            
            # ⭐ FORMAT KHUSUS UNTUK KOLOM KOSONG (Mencabut Warna, Efek Tebal & Garis Pembatas)
            gap_header_fmt = wb.add_format({'bg_color': '#ffffff', 'border': 0})
            gap_cell_fmt = wb.add_format({'bg_color': '#ffffff', 'border': 0})
            
            # Render Sheet Ringkasan
            if df_sum is not None:
                df_sum.to_excel(writer, sheet_name='Ringkasan', index=False, startrow=4)
                ws = writer.sheets['Ringkasan']
                ws.write('A1', 'LAPORAN REKONSILIASI PENGADAAN BARANG DAN JASA', title_fmt)
                ws.write('A2', f'Satuan Kerja: {satker.upper()}')
                for col_num, value in enumerate(df_sum.columns.values):
                    ws.write(4, col_num, value, header_fmt)
                    ws.set_column(col_num, col_num, 25)
                for row in range(len(df_sum)):
                    ws.write(row+5, 1, df_sum.iloc[row, 1], curr_fmt)
                    ws.write(row+5, 2, df_sum.iloc[row, 2], curr_fmt)
                    ws.write(row+5, 3, df_sum.iloc[row, 3], curr_fmt)
                    ws.write(row+5, 4, df_sum.iloc[row, 4], pct_fmt)

            # Render Sheet Rincian Kategori (Termasuk Logika Jarak Kolom Sanding)
            for name, df_d in dict_detail.items():
                if len(df_d) > 0:
                    df_idx = add_index(df_d)
                    df_idx.to_excel(writer, sheet_name=name[:31], index=False)
                    ws_d = writer.sheets[name[:31]]
                    
                    # 1. Atur Tampilan Header
                    for col_num, value in enumerate(df_idx.columns.values):
                        if str(value).strip() == '':  # Jika nama kolom hanya berupa space (kolom jarak)
                            ws_d.write(0, col_num, '', gap_header_fmt)
                            ws_d.set_column(col_num, col_num, 4)  # Buat kolom jarak berukuran sempit (lebar 4)
                        else:
                            ws_d.write(0, col_num, value, header_fmt)
                            ws_d.set_column(col_num, col_num, 24) # Kolom biasa berukuran standar lebar 24
                    
                    # 2. Atur Tampilan Sel Konten Data
                    for r_idx in range(len(df_idx)):
                        for c_idx, col_name in enumerate(df_idx.columns):
                            val = df_idx.iloc[r_idx, c_idx]
                            
                            if str(col_name).strip() == '': # Jika kolom jarak, paksa kosong tanpa border
                                ws_d.write(r_idx+1, c_idx, '', gap_cell_fmt)
                            elif any(keyword in str(col_name).lower() for keyword in ['nilai', 'pagu', 'anggaran', 'selisih']):
                                ws_d.write(r_idx+1, c_idx, pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0, curr_fmt)
                            else:
                                ws_d.write(r_idx+1, c_idx, str(val) if pd.notnull(val) else '', text_fmt)
                                
                    ws_d.set_column(0, 0, 6)  # Khusus lebar kolom No indeks urut di awal
        return out.getvalue()

    col_dl1, col_dl2 = st.columns([1, 1])
    with col_dl1:
        st.subheader("Laporan Keseluruhan (Buku)")
        master_excel = generate_excel_with_gap(df_laporan, dict_all_data, satker_terpilih)
        st.download_button(
            label="📁 UNDUH BUKU LAPORAN LENGKAP (Excel)",
            data=master_excel,
            file_name=f"Laporan_Rekonsiliasi_Total_{satker_terpilih.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
        st.caption("*Mencakup lembar Sanding_Detail_Berjarak dengan desain interior sel kolom kosong tanpa border.*")

    with col_dl2:
        st.subheader("Unduhan Per Kategori (Parsial)")
        with st.expander("Buka Pilihan Unduh Satuan"):
            for name, df_d in dict_all_data.items():
                partial_excel = generate_excel_with_gap(None, {name: df_d}, satker_terpilih)
                st.download_button(
                    label=f"📄 Unduh {name.replace('_', ' ')}",
                    data=partial_excel,
                    file_name=f"Data_{name}_{satker_terpilih.replace(' ','_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
