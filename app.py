import streamlit as st
import pandas as pd
import io

# ==============================================================================
# 1. KONFIGURASI HALAMAN & TEMA VISUAL (UI YANG LEBIH MODERN)
# ==============================================================================
st.set_page_config(page_title="Dashboard Rekonsiliasi PBJ", layout="wide", page_icon="📊")

# CSS Kustom untuk mempercantik kartu metrik dan tabel
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

# ==============================================================================
# 2. INISIALISASI SESSION STATE (Mencegah AttributeError)
# ==============================================================================
if "data_proses" not in st.session_state:
    st.session_state.data_proses = None

# ==============================================================================
# 3. HEADER & SIDEBAR
# ==============================================================================
col_logo, col_title = st.columns([1, 8])
with col_logo:
    # Ganti dengan path logo Pemprov jika ada, atau gunakan icon default
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
# 4. LOGIKA PEMROSESAN DATA UTAMA
# ==============================================================================
if file_ren and file_real and tombol_proses:
    with st.spinner('Menyelaraskan data RUP dan Realisasi...'):
        df_ren = pd.read_csv(file_ren)
        df_real = pd.read_csv(file_real)
        val_col = 'Total Nilai (Rp)'
        rup_col = 'Kode RUP'

        # Standardisasi kolom
        df_ren.columns = df_ren.columns.str.strip()
        df_real.columns = df_real.columns.str.strip()
        
        for df in [df_ren, df_real]:
            if rup_col in df.columns: df[rup_col] = df[rup_col].astype(str).str.strip()
            if 'Metode Pengadaan' in df.columns: df['Metode Pengadaan'] = df['Metode Pengadaan'].astype(str).str.lower()
            if 'Sumber Transaksi' in df.columns: df['Sumber Transaksi'] = df['Sumber Transaksi'].astype(str).str.lower().str.strip()
            if 'Cara Pengadaan' in df.columns: df['Cara Pengadaan'] = df['Cara Pengadaan'].astype(str).str.lower()
            if 'Nama Satuan Kerja' in df.columns: df['Nama Satuan Kerja'] = df['Nama Satuan Kerja'].astype(str).str.strip()

        # Konversi ke numerik dan hapus duplikasi
        df_ren[val_col] = pd.to_numeric(df_ren[val_col], errors='coerce').fillna(0)
        df_real[val_col] = pd.to_numeric(df_real[val_col], errors='coerce').fillna(0)
        df_ren = df_ren.drop_duplicates(subset=[rup_col])
        df_real = df_real.drop_duplicates(subset=[rup_col])

        st.session_state.data_proses = {
            "df_ren": df_ren, "df_real": df_real, "val_col": val_col, "rup_col": rup_col
        }
        st.success("Data berhasil diproses!")

# ==============================================================================
# 5. RENDER DASHBOARD & LAPORAN
# ==============================================================================
if st.session_state.get("data_proses") is not None:
    dp = st.session_state["data_proses"]
    df_ren, df_real = dp["df_ren"], dp["df_real"]
    val_col, rup_col = dp["val_col"], dp["rup_col"]

    # Filter Satuan Kerja
    list_satker = ["Semua Satuan Kerja"] + sorted(df_ren['Nama Satuan Kerja'].dropna().unique())
    satker_terpilih = st.sidebar.selectbox("Tampilkan Data Unit Kerja:", list_satker)

    # Filter Logika
    if satker_terpilih != "Semua Satuan Kerja":
        df_ren = df_ren[df_ren['Nama Satuan Kerja'] == satker_terpilih] if 'Nama Satuan Kerja' in df_ren.columns else df_ren
        df_real = df_real[df_real['Nama Satuan Kerja'] == satker_terpilih] if 'Nama Satuan Kerja' in df_real.columns else df_real

    # Klasifikasi Data (Penyedia vs Swakelola)
    df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)]
    df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)]
    
    df_ren_swa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
    df_real_swa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]

    # Pemetaan Rekonsiliasi
    df_real_penyedia_sum = df_real_penyedia.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'})
    df_sesuai = pd.merge(df_ren_penyedia, df_real_penyedia_sum, on=rup_col, how='inner')
    df_real_only = df_real_penyedia[~df_real_penyedia[rup_col].isin(df_ren_penyedia[rup_col])]
    df_belum_teralisasi = df_ren_penyedia[~df_ren_penyedia[rup_col].isin(df_real_penyedia[rup_col])]

    df_swakelola_tercatat = pd.merge(df_ren_swa, df_real_swa.groupby(rup_col, as_index=False)[val_col].sum().rename(columns={val_col:'Anggaran_Realisasi'}), on=rup_col, how='inner')
    df_swakelola_tidak_tercatat = df_ren_swa[~df_ren_swa[rup_col].isin(df_real_swa[rup_col])]

    # Ekstraksi Transaksi Spesifik
    df_ekatalog = df_real[df_real['Sumber Transaksi'].str.contains('e-katalog|katalog', na=False)]
    df_tokodaring = df_real[df_real['Sumber Transaksi'].str.contains('tokodaring', na=False)]

    # Fungsi Bantuan
    def hitung(df, col): return len(df), df[col].sum() if col in df.columns else 0
    def add_index(df):
        df_idx = df.copy()
        df_idx.insert(0, "No", range(1, len(df)+1))
        return df_idx

    # --- TAMPILAN METRIK REKONSILIASI KANBAN ---
    st.markdown("---")
    st.subheader("Ringkasan Status Rekonsiliasi Anggaran")
    
    kategori_cards = [
        ("Sesuai RUP", df_sesuai, 'Anggaran_Realisasi'),
        ("Hanya Realisasi", df_real_only, val_col),
        ("Belum Terealisasi", df_belum_teralisasi, val_col),
        ("E-Katalog 6.0", df_ekatalog, val_col)
    ]
    
    cols = st.columns(4)
    for idx, (label, df_cat, col_val) in enumerate(kategori_cards):
        pkt, ang = hitung(df_cat, col_val)
        cols[idx].markdown(f"""
        <div class='stat-card'>
            <div class='stat-label'>{label}</div>
            <div class='stat-value-pkt'>{pkt} Paket</div>
            <div class='stat-value-rp'>Rp {ang:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    # --- TABEL LAPORAN EKSEKUTIF (FORMAL) ---
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
        "Capaian (%)": [
            (real_penyedia / pagu_penyedia) if pagu_penyedia > 0 else 0,
            (real_swa / pagu_swa) if pagu_swa > 0 else 0,
            ((real_penyedia + real_swa) / (pagu_penyedia + pagu_swa)) if (pagu_penyedia + pagu_swa) > 0 else 0
        ]
    })
    
    st.table(df_laporan.style.format({
        "Pagu Perencanaan (SIRUP)": "Rp {:,.0f}",
        "Realisasi Tercatat": "Rp {:,.0f}",
        "Gap (Selisih)": "Rp {:,.0f}",
        "Capaian (%)": "{:.2%}"
    }).set_properties(**{'background-color': '#ffffff', 'color': 'black', 'border-color': '#e0e0e0'}))

    # --- TAB DETAIL DATA ---
    st.markdown("### Rincian Data per Kategori")
    tab_titles = ["✅ Sesuai RUP", "⚠️ Hanya Realisasi", "⏳ Belum Realisasi", "🛒 E-Katalog 6.0", "🏪 Toko Daring", "📝 Swakelola"]
    tab_dfs = [df_sesuai, df_real_only, df_belum_teralisasi, df_ekatalog, df_tokodaring, df_swakelola_tercatat]
    
    tabs = st.tabs(tab_titles)
    for tab, df_tab in zip(tabs, tab_dfs):
        with tab:
            st.dataframe(add_index(df_tab), use_container_width=True)

    # ==============================================================================
    # 6. MODUL EXPORT EXCEL
    # ==============================================================================
    st.markdown("---")
    st.header("📥 Pusat Unduhan Laporan")
    
    dict_all_data = {
        "Sesuai_RUP": df_sesuai,
        "Hanya_Realisasi": df_real_only,
        "Belum_Terealisasi": df_belum_teralisasi,
        "E-Katalog_6.0": df_ekatalog,
        "Toko_Daring": df_tokodaring,
        "Swakelola_Tercatat": df_swakelola_tercatat,
        "Swakelola_Sisa": df_swakelola_tidak_tercatat
    }

    # Fungsi Bantuan Format Excel
    def generate_excel(df_sum, dict_detail, satker):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            wb = writer.book
            title_fmt = wb.add_format({'bold': True, 'font_size': 14, 'font_name': 'Arial'})
            header_fmt = wb.add_format({'bold': True, 'bg_color': '#0c2461', 'color': 'white', 'border': 1, 'align': 'center'})
            curr_fmt = wb.add_format({'num_format': '#,##0', 'border': 1})
            pct_fmt = wb.add_format({'num_format': '0.00%', 'border': 1})
            
            # Tulis Laporan Utama (Hanya jika laporan penuh)
            if df_sum is not None:
                df_sum.to_excel(writer, sheet_name='Ringkasan', index=False, startrow=4)
                ws = writer.sheets['Ringkasan']
                ws.write('A1', 'LAPORAN REKONSILIASI PENGADAAN BARANG DAN JASA', title_fmt)
                ws.write('A2', f'Satuan Kerja: {satker.upper()}')
                for col_num, value in enumerate(df_sum.columns.values):
                    ws.write(4, col_num, value, header_fmt)
                    ws.set_column(col_num, col_num, 22)
                for row in range(len(df_sum)):
                    ws.write(row+5, 1, df_sum.iloc[row, 1], curr_fmt)
                    ws.write(row+5, 2, df_sum.iloc[row, 2], curr_fmt)
                    ws.write(row+5, 3, df_sum.iloc[row, 3], curr_fmt)
                    ws.write(row+5, 4, df_sum.iloc[row, 4], pct_fmt)

            # Tulis Sheet Detail
            for name, df_d in dict_detail.items():
                if len(df_d) > 0:
                    df_idx = add_index(df_d)
                    df_idx.to_excel(writer, sheet_name=name[:31], index=False)
                    ws_d = writer.sheets[name[:31]]
                    for col_num, value in enumerate(df_idx.columns.values):
                        ws_d.write(0, col_num, value, header_fmt)
                    ws_d.set_column(0, len(df_idx.columns), 18)
        return out.getvalue()

    # Tombol Unduh Laporan Penuh (Master)
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
        st.caption("*Mencakup tabel ringkasan eksekutif dan seluruh tab data mentah.*")

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
