import streamlit as st
import pandas as pd
import io

# ==============================================================================
# 1. KONFIGURASI HALAMAN & TEMA VISUAL DASHBOARD
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
# 2. HEADER UTAMA & FILTER SIDEBAR
# ==============================================================================
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("<h1>📊</h1>", unsafe_allow_html=True) 
with col_title:
    st.title("Sistem Rekonsiliasi SIRUP & Realisasi")
    st.markdown("Analisis Komprehensif Data Perencanaan vs Realisasi Anggaran")

with st.sidebar:
    st.header("📂 Unggah Berkas")
    st.info("Format berkas yang didukung: CSV atau Excel (.xlsx / .xls) resmi dari sistem.")
    
    # PERUBAHAN DI SINI: Menambahkan jenis berkas excel ke parameter type
    file_ren = st.file_uploader("1. Data Perencanaan (RUP)", type=['csv', 'xlsx', 'xls'])
    file_real = st.file_uploader("2. Data Realisasi", type=['csv', 'xlsx', 'xls'])
    
    tombol_proses = st.button("🔄 Proses Data Rekonsiliasi", use_container_width=True, type="primary")
    st.divider()

# ==============================================================================
# 3. ENGINE PEMROSESAN & STANDARDISASI DATA
# ==============================================================================
if file_ren and file_real and tombol_proses:
    with st.spinner('Menyelaraskan data RUP dan Realisasi...'):
        
        # PERUBAHAN DI SINI: Logika fungsi pembaca berkas adaptif otomatis
        def baca_berkas(file_obj):
            if file_obj.name.endswith('.csv'):
                return pd.read_csv(file_obj)
            else:
                return pd.read_excel(file_obj)
        
        df_ren = baca_berkas(file_ren)
        df_real = baca_berkas(file_real)
        
        # Kamus Pemetaan Kolom Pintar Otomatis
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
        
        # Pembersihan Nominal Anggaran
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

        # Pembersihan Teks Kolom Utama
        for df in [df_ren, df_real]:
            for col in ['Metode Pengadaan', 'Sumber Transaksi', 'Cara Pengadaan', 'Nama Satuan Kerja', 'Nama Penyedia', 'Nama Paket']:
                if col in df.columns:
                    df[col] = df[col].fillna('').astype(str).str.strip()

        # Hilangkan duplikasi data pada Master Perencanaan (RUP) untuk basis pencarian
        df_ren_clean = df_ren[df_ren[rup_col].str.lower() != 'nan'].drop_duplicates(subset=[rup_col])

        st.session_state.data_proses = {
            "df_ren": df_ren_clean, "df_real": df_real, "val_col": val_col, "rup_col": rup_col
        }
        st.success("Data berhasil diselaraskan!")

# ==============================================================================
# 4. RENDER VISUAL DASHBOARD & TABULAR PREVIEW
# ==============================================================================
if st.session_state.get("data_proses") is not None:
    dp = st.session_state["data_proses"]
    df_ren, df_real = dp["df_ren"], dp["df_real"]
    val_col, rup_col = dp["val_col"], dp["rup_col"]

    # Filter Satuan Kerja Global pada Sidebar
    list_satker = ["Semua Satuan Kerja"] + sorted(df_ren['Nama Satuan Kerja'].dropna().unique())
    satker_terpilih = st.sidebar.selectbox("Tampilkan Data Unit Kerja:", list_satker)

    if satker_terpilih != "Semua Satuan Kerja":
        df_ren = df_ren[df_ren['Nama Satuan Kerja'] == satker_terpilih] if 'Nama Satuan Kerja' in df_ren.columns else df_ren
        df_real = df_real[df_real['Nama Satuan Kerja'] == satker_terpilih] if 'Nama Satuan Kerja' in df_real.columns else df_real

    # Klasifikasi Penyedia vs Swakelola
    df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False, case=False)]
    df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False, case=False)]
    
    df_ren_swa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False, case=False)]
    df_real_swa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False, case=False)]

    # Agregasi untuk Metrik Ringkasan Atas
    agg_dict = {val_col: 'sum'}
    if 'Nama Penyedia' in df_real.columns:
        agg_dict['Nama Penyedia'] = lambda x: '; '.join(dict.fromkeys([
            str(s).strip() for s in x if str(s).strip().lower() not in ['', 'nan', 'none', '-']
        ]))
    df_real_penyedia_sum = df_real_penyedia.groupby(rup_col, as_index=False).agg(agg_dict).rename(columns={val_col:'Anggaran_Realisasi'})
    
    df_ren_penyedia_clean = df_ren_penyedia.drop(columns=['Nama Penyedia']) if 'Nama Penyedia' in df_ren_penyedia.columns else df_ren_penyedia
    df_sesuai = pd.merge(df_ren_penyedia_clean, df_real_penyedia_sum, on=rup_col, how='inner')

    # Pembuatan Struktur Kolom Sanding
    df_sanding_raw = pd.merge(df_ren_penyedia, df_real_penyedia, on=rup_col, how='inner', suffixes=('_Rencana', '_Realisasi'))
    df_sanding_raw['Selisih Transaksi (Rp)'] = df_sanding_raw['Total Nilai (Rp)_Rencana'] - df_sanding_raw['Total Nilai (Rp)_Realisasi']

    kolom_sanding_urut = [
        rup_col, 'Nama Satuan Kerja_Rencana', 'Nama Paket_Rencana', 'Total Nilai (Rp)_Rencana',
        'Nama Penyedia_Realisasi', 'Total Nilai (Rp)_Realisasi', 'Selisih Transaksi (Rp)',
        'Sumber Transaksi_Realisasi', 'Metode Pengadaan_Rencana'
    ]

    kolom_final_sanding = [c for c in kolom_sanding_urut if c in df_sanding_raw.columns]
    kolom_sisa_sanding = [c for c in df_sanding_raw.columns if c not in kolom_final_sanding]
    df_sanding = df_sanding_raw[kolom_final_sanding + kolom_sisa_sanding].sort_values(by=[rup_col]).reset_index(drop=True)

    mapping_nama_kolom = {
        'Nama Satuan Kerja_Rencana': 'Nama OPD',
        'Nama Paket_Rencana': 'Nama Paket Perencanaan (SIRUP)',
        'Total Nilai (Rp)_Rencana': 'Pagu Rencana (SIRUP)',
        'Nama Penyedia_Realisasi': 'Nama Penyedia (Realisasi)',
        'Total Nilai (Rp)_Realisasi': 'Nilai Riil Realisasi',
        'Sumber Transaksi_Realisasi': 'Platform Realisasi',
        'Metode Pengadaan_Rencana': 'Metode Pemilihan'
    }
    df_sanding_view = df_sanding.rename(columns=mapping_nama_kolom)

    # Filter Kategori Sampingan
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

    # --- RINGKASAN METRIK UTAMA ---
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

    # --- TABEL EKSEKUTIF ---
    st.markdown("---")
    st.subheader("📋 Laporan Ringkasan Executive")
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

    # --- TAB PREVIEW DATA DASHBOARD ---
    st.markdown("### Rincian Data per Kategori")
    tab_titles = ["🔍 Detail Sanding RUP (Rapi)", "✅ Sesuai RUP (Agregat)", "⚠️ Hanya Realisasi", "⏳ Belum Realisasi", "🛒 E-Katalog 6.0", "🏪 Toko Daring"]
    tab_dfs = [df_sanding_view, df_sesuai, df_real_only, df_belum_teralisasi, df_ekatalog, df_tokodaring]
    
    tabs = st.tabs(tab_titles)
    for tab, df_tab in zip(tabs, tab_dfs):
        with tab:
            st.dataframe(add_index(df_tab), use_container_width=True)

# ==============================================================================
# 5. LAPORAN REKAPITULASI BERDASARKAN OPD
# ==============================================================================
    st.markdown("---")
    st.subheader("🏢 Laporan Rekapitulasi Berdasarkan OPD")
    with st.spinner("Menyusun rekapitulasi data per OPD..."):
        master_ren, master_real = st.session_state.data_proses["df_ren"], st.session_state.data_proses["df_real"]
        v_col, r_col = st.session_state.data_proses["val_col"], st.session_state.data_proses["rup_col"]
        semua_opd = sorted(list(set(master_ren['Nama Satuan Kerja'].dropna()) | set(master_real['Nama Satuan Kerja'].dropna())))
        data_rekap_opd = []

        for opd in semua_opd:
            ren_opd = master_ren[master_ren['Nama Satuan Kerja'] == opd]
            real_opd = master_real[master_real['Nama Satuan Kerja'] == opd]
            r_penyedia = ren_opd[~ren_opd['Metode Pengadaan'].str.contains('swakelola', na=False, case=False)]
            rup_pen_pkt, rup_pen_ang = len(r_penyedia), r_penyedia[v_col].sum()
            r_swa = ren_opd[ren_opd['Cara Pengadaan'].str.contains('swakelola', na=False, case=False)]
            rup_swa_pkt, rup_swa_ang = len(r_swa), r_swa[v_col].sum()
            rl_swa = real_opd[real_opd['Sumber Transaksi'].str.contains('swakelola', na=False, case=False)]
            real_swa_pkt, real_swa_ang = len(rl_swa), rl_swa[v_col].sum()
            rl_penyedia = real_opd[~real_opd['Metode Pengadaan'].str.contains('swakelola', na=False, case=False)]
            sesuai_df = rl_penyedia[rl_penyedia[r_col].isin(r_penyedia[r_col])]
            real_pen_sesuai_pkt, real_pen_sesuai_ang = sesuai_df[r_col].nunique(), sesuai_df[v_col].sum()
            tdk_sesuai_df = rl_penyedia[~rl_penyedia[r_col].isin(r_penyedia[r_col])]
            real_pen_tdk_pkt, real_pen_tdk_ang = len(tdk_sesuai_df), tdk_sesuai_df[v_col].sum()
            td_df = rl_penyedia[rl_penyedia['Sumber Transaksi'].str.contains('tokodaring', na=False, case=False)]
            td_pkt, td_ang = len(td_df), td_df[v_col].sum()
            pdn_ang = rl_penyedia[rl_penyedia['Status PDN'].astype(str).str.contains('ya|pdn', na=False, case=False)][v_col].sum() if 'Status PDN' in rl_penyedia.columns else 0
            selisih_pkt = rup_pen_pkt - (real_pen_sesuai_pkt + real_pen_tdk_pkt + td_pkt)
            selisih_ang = rup_pen_ang - (real_pen_sesuai_ang + real_pen_tdk_ang + td_ang)
            data_rekap_opd.append([opd, rup_pen_pkt, rup_pen_ang, rup_swa_pkt, rup_swa_ang, real_swa_pkt, real_swa_ang, real_pen_sesuai_pkt, real_pen_sesuai_ang, real_pen_tdk_pkt, real_pen_tdk_ang, td_pkt, td_ang, pdn_ang, selisih_pkt, selisih_ang])

        struktur_kolom = pd.MultiIndex.from_tuples([
            ("Nama OPD", "", ""), ("RUP", "Penyedia", "Paket"), ("RUP", "Penyedia", "Anggaran"), ("RUP", "Swakelola", "Paket"), ("RUP", "Swakelola", "Anggaran"), ("Realisasi", "Swakelola", "Paket"), ("Realisasi", "Swakelola", "Anggaran"), ("Realisasi", "Penyedia", "Paket Sesuai RUP"), ("Realisasi", "Penyedia", "Anggaran Sesuai RUP"), ("Realisasi", "Penyedia", "Paket Tdk Sesuai RUP"), ("Realisasi", "Penyedia", "Anggaran Tdk Sesuai"), ("Realisasi", "Penyedia", "Paket Toko Daring"), ("Realisasi", "Penyedia", "Anggaran Toko Daring"), ("Realisasi", "Penyedia", "Nilai PDN"), ("Realisasi", "Selisih Bersih (Sisa RUP)", "Paket"), ("Realisasi", "Selisih Bersih (Sisa RUP)", "Anggaran")
        ])
        df_laporan_opd = pd.DataFrame(data_rekap_opd, columns=struktur_kolom)
        df_laporan_opd.insert(0, ("No", "", ""), range(1, len(df_laporan_opd) + 1)) 
        st.dataframe(df_laporan_opd, use_container_width=True)

        buffer_opd = io.BytesIO()
        with pd.ExcelWriter(buffer_opd, engine='xlsxwriter') as writer_opd:
            df_laporan_opd.set_index(("No", "", "")).to_excel(writer_opd, sheet_name='Rekap_OPD', index=True)
            ws_opd = writer_opd.sheets['Rekap_OPD']
            ws_opd.set_column(0, 0, 5)
            ws_opd.set_column(1, 1, 35)
            ws_opd.set_column(2, 17, 15)
        st.download_button(label="📥 Unduh Rekap OPD (Excel)", data=buffer_opd.getvalue(), file_name="Laporan_Rekap_OPD.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

# ==============================================================================
# 6. ENGINE FILE EXPORT EXCEL
# ==============================================================================
    st.markdown("---")
    st.header("📥 Pusat Unduhan Laporan")
    
    dict_all_data = {
        "Sanding_Detail_RUP": df_sanding_view, 
        "Sesuai_RUP_Agregat": df_sesuai,
        "Hanya_Realisasi": df_real_only,
        "Belum_Terealisasi": df_belum_teralisasi,
        "E-Katalog_6.0": df_ekatalog,
        "Toko_Daring": df_tokodaring
    }

    def generate_excel(df_sum, dict_detail, satker):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            wb = writer.book
            title_fmt = wb.add_format({'bold': True, 'font_size': 14, 'font_name': 'Arial', 'color': '#0c2461'})
            section_fmt = wb.add_format({'bold': True, 'font_size': 11, 'font_name': 'Arial', 'color': '#2c3e50', 'bg_color': '#f1f2f6', 'border': 1})
            header_fmt = wb.add_format({'bold': True, 'bg_color': '#0c2461', 'color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
            curr_fmt = wb.add_format({'num_format': '#,##0', 'border': 1, 'valign': 'vcenter'})
            pct_fmt = wb.add_format({'num_format': '0.00%', 'border': 1, 'valign': 'vcenter'})
            text_fmt = wb.add_format({'border': 1, 'valign': 'vcenter'})
            
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

            for name, df_d in dict_detail.items():
                if len(df_d) > 0:
                    if name == "Sanding_Detail_RUP":
                        ws_s = wb.add_worksheet("Sanding_Detail_RUP")
                        writer.sheets["Sanding_Detail_RUP"] = ws_s
                        
                        ws_s.write('A1', 'LAPORAN REKONSILIASI DATA PBJ (SANDING SIDE-BY-SIDE)', title_fmt)
                        ws_s.write('A2', f'Unit Kerja / Satker: {satker.upper()}')
                        
                        ws_s.merge_range('A4:E4', ' TABEL PERENCANAAN (MASTER SIRUP)', section_fmt)
                        ws_s.merge_range('H4:M4', ' TABEL EKSEKUSI REALISASI (PLATFORM KONTRAK)', section_fmt)
                        
                        headers_left = ['No Rencana', 'Kode RUP', 'Nama OPD', 'Nama Paket Perencanaan (SIRUP)', 'Pagu Rencana (SIRUP)']
                        headers_right = ['No Realisasi', 'Nama Penyedia (Realisasi)', 'Nilai Riil Realisasi', 'Selisih Transaksi (Rp)', 'Platform Realisasi', 'Metode Pemilihan']
                        
                        for col_idx, text in enumerate(headers_left):
                            ws_s.write(4, col_idx, text, header_fmt)
                            ws_s.set_column(col_idx, col_idx, 22 if col_idx > 0 else 12)
                            
                        for col_idx, text in enumerate(headers_right):
                            ws_s.write(4, col_idx + 7, text, header_fmt)
                            ws_s.set_column(col_idx + 7, col_idx + 7, 22 if col_idx > 0 else 12)
                            
                        ws_s.set_column(5, 5, 3) 
                        ws_s.set_column(6, 6, 3) 
                        
                        last_rup = None
                        idx_rencana = 0
                        idx_realisasi = 0
                        
                        df_sanding_clean = df_d.reset_index(drop=True)
                        
                        for idx, row_data in df_sanding_clean.iterrows():
                            excel_row = idx + 5
                            current_rup = str(row_data.get('Kode RUP', '')).strip()
                            
                            if current_rup != last_rup:
                                idx_rencana += 1
                                idx_realisasi = 1 
                                
                                ws_s.write(excel_row, 0, idx_rencana, text_fmt)
                                ws_s.write(excel_row, 1, current_rup, text_fmt)
                                ws_s.write(excel_row, 2, str(row_data.get('Nama OPD', '')), text_fmt)
                                ws_s.write(excel_row, 3, str(row_data.get('Nama Paket Perencanaan (SIRUP)', '')), text_fmt)
                                ws_s.write(excel_row, 4, float(row_data.get('Pagu Rencana (SIRUP)', 0)), curr_fmt)
                                last_rup = current_rup
                            else:
                                idx_realisasi += 1
                                for c_left in range(5):
                                    ws_s.write(excel_row, c_left, '', text_fmt)
                                    
                            ws_s.write(excel_row, 7, idx_realisasi, text_fmt)
                            ws_s.write(excel_row, 8, str(row_data.get('Nama Penyedia (Realisasi)', '')), text_fmt)
                            ws_s.write(excel_row, 9, float(row_data.get('Nilai Riil Realisasi', 0)), curr_fmt)
                            ws_s.write(excel_row, 10, float(row_data.get('Selisih Transaksi (Rp)', 0)), curr_fmt)
                            ws_s.write(excel_row, 11, str(row_data.get('Platform Realisasi', '')), text_fmt)
                            ws_s.write(excel_row, 12, str(row_data.get('Metode Pemilihan', '')), text_fmt)
                    else:
                        df_idx = add_index(df_d)
                        df_idx.to_excel(writer, sheet_name=name[:31], index=False)
                        ws_d = writer.sheets[name[:31]]
                        
                        for col_num, value in enumerate(df_idx.columns.values):
                            ws_d.write(0, col_num, value, header_fmt)
                            
                        for r_idx in range(len(df_idx)):
                            for c_idx, col_name in enumerate(df_idx.columns):
                                val = df_idx.iloc[r_idx, c_idx]
                                if any(keyword in str(col_name).lower() for keyword in ['nilai', 'pagu', 'anggaran', 'selisih']):
                                    ws_d.write(r_idx+1, c_idx, pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0, curr_fmt)
                                else:
                                    ws_d.write(r_idx+1, c_idx, str(val) if pd.notnull(val) else '', text_fmt)
                                    
                        ws_d.set_column(0, 0, 6)
                        ws_d.set_column(1, len(df_idx.columns)-1, 24)
        return out.getvalue()

    col_dl1, col_dl2 = st.columns([1, 1])
    with col_dl1:
        st.subheader("Laporan Keseluruhan (Buku)")
        master_excel = generate_excel(df_laporan, dict_all_data, satker_terpilih)
        st.download_button(
            label="📁 UNDUH BUKU LAPORAN LENGKAP (Excel)",
            data=master_excel,
            file_name=f"Laporan_Rekonsiliasi_Total_{satker_terpilih.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
        st.caption("*Catatan: Khusus lembar 'Sanding_Detail_RUP' di Excel, baris RUP duplikat otomatis di-blank agar pagu anggaran tidak ganda.*")

    with col_dl2:
        st.subheader("Unduhan Per Kategori (Parsial)")
        with st.expander("Buka Pilihan Unduh Satuan"):
            for name, df_d in dict_all_data.items():
                partial_excel = generate_excel(None, {name: df_d}, satker_terpilih)
                st.download_button(
                    label=f"📄 Unduh {name.replace('_', ' ')}",
                    data=partial_excel,
                    file_name=f"Data_{name}_{satker_terpilih.replace(' ','_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
