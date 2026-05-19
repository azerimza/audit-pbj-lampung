import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="REKONSILIASI DATA", layout="wide")

st.markdown("""
    <style>
    .stat-card {
        background-color: #ffffff; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 5px solid #0c2461;
        text-align: center; margin-bottom: 20px;
    }
    .stat-label { font-size: 14px; color: #555; font-weight: bold; }
    .stat-value { font-size: 24px; color: #0c2461; font-weight: bold; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def read_csv_smart(file):
    try:
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
    except:
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='cp1252')

# --- 2. SIDEBAR ---
with st.sidebar:
    col1, col2, col3 = st.columns([1, 2, 1]) 
    with col2:
        try:
            st.image("LOGO PEMPROV BARU.png", width=60)
        except:
            st.warning("Logo tidak ditemukan")
            
    st.markdown("<h3 style='text-align: center; margin-top: -10px;'>PEMBINAAN DAN ADVOKASI</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'><b>Reza Saputra Azmi</b></p>", unsafe_allow_html=True)
    st.divider()
    
    file_ren = st.file_uploader("1. Upload Data SIRUP", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])

# --- 3. LOGIKA PEMROSESAN ---
if file_ren and file_real:
    df_ren_raw, df_real_raw = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col, rup_col, satker_col = 'Total Nilai (Rp)', 'Kode RUP', 'Nama Satuan Kerja'
    
    # Bersihkan nama kolom
    df_ren_raw.columns = df_ren_raw.columns.str.strip()
    df_real_raw.columns = df_real_raw.columns.str.strip()

    # Paksa Kode RUP jadi String & Bersihkan Spasi
    df_ren_raw[rup_col] = df_ren_raw[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)
    df_real_raw[rup_col] = df_real_raw[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    # Sinkronisasi Nama Satker agar pencocokan teks antar-file tidak miss
    df_ren_raw[satker_col] = df_ren_raw[satker_col].astype(str).str.strip()
    df_real_raw[satker_col] = df_real_raw[satker_col].astype(str).str.strip()

    for df in [df_ren_raw, df_real_raw]:
        if val_col in df.columns:
            df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # =====================================================================
    # PEMISAHAN LOGIKAL MUTLAK: SWAKELOLA vs PENYEDIA SEJAK AWAL
    # =====================================================================
    # 1. Dataset Jalur Swakelola
    df_ren_swa = df_ren_raw[df_ren_raw['Metode Pengadaan'].astype(str).str.lower().str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_ren_raw.columns else pd.DataFrame(columns=df_ren_raw.columns)
    df_real_swa = df_real_raw[df_real_raw['Metode Pengadaan'].astype(str).str.lower().str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_real_raw.columns else pd.DataFrame(columns=df_real_raw.columns)

    # 2. Dataset Jalur Penyedia (Garansi Bebas Teks Swakelola)
    df_ren = df_ren_raw[~df_ren_raw['Metode Pengadaan'].astype(str).str.lower().str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_ren_raw.columns else df_ren_raw.copy()
    df_real = df_real_raw[~df_real_raw['Metode Pengadaan'].astype(str).str.lower().str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_real_raw.columns else df_real_raw.copy()

    # Identifikasi Kategori Khusus Penyedia
    def map_kat(m):
        m = str(m).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Tokodaring'
        if 'katalog' in m: return 'E-Katalog'
        return 'Penyedia Lainnya'

    df_real['Kat_Audit'] = df_real['Metode Pengadaan'].apply(map_kat) if 'Metode Pengadaan' in df_real.columns else 'Lainnya'
    
    # Agregasi data realisasi penyedia berdasarkan RUP & Satker
    df_real_agg = df_real.groupby([rup_col, satker_col]).agg({
        val_col: 'sum', 'Kat_Audit': 'first'
    }).reset_index()

# --- 4. PANEL FILTER UTAMA ---
    st.title("📊 Dashboard Audit & Rekonsiliasi (Terpisah Per Jalur)")
    
    f1, f2, f3 = st.columns([2, 2, 1])
    with f1:
        list_satker_pilihan = ["Semua OPD / Satker"] + sorted(df_ren_raw[satker_col].dropna().unique().tolist())
        satker_terpilih = st.selectbox("🔍 Pilih OPD / Instansi:", list_satker_pilihan)
    with f2:
        opsi_proses = st.selectbox("⚙️ Pilih Jenis Analisis Laporan:", [
            "1. Laporan Keseluruhan (Penyedia & Swakelola Terpisah)",
            "2. Laporan Paket Tidak Terealisasi Saja (Penyedia)",
            "3. Laporan Khusus Toko Daring"
        ])
    with f3:
        st.markdown("<br>", unsafe_allow_html=True)
        tombol_proses = st.button("🚀 Proses Data", use_container_width=True)

    if 'proses_dijalankan' not in st.session_state:
        st.session_state.proses_dijalankan = False
    if 'satker_aktif' not in st.session_state:
        st.session_state.satker_aktif = ""
    if 'opsi_aktif' not in st.session_state:
        st.session_state.opsi_aktif = ""

    if tombol_proses:
        st.session_state.proses_dijalankan = True
        st.session_state.satker_aktif = satker_terpilih
        st.session_state.opsi_aktif = opsi_proses

    # --- JALANKAN EKSEKUSI DATA ---
    if st.session_state.proses_dijalankan:
        satker_jalan = st.session_state.satker_aktif
        opsi_jalan = st.session_state.opsi_aktif

        # Filter Dataset berdasarkan scope OPD
        if satker_jalan == "Semua OPD / Satker":
            df_ren_filtered = df_ren
            df_real_filtered = df_real
            df_real_agg_filtered = df_real_agg
            df_ren_swa_filtered = df_ren_swa
            df_real_swa_filtered = df_real_swa
            satker_loop_list = sorted(df_ren_raw[satker_col].dropna().unique())
        else:
            df_ren_filtered = df_ren[df_ren[satker_col] == satker_jalan]
            df_real_filtered = df_real[df_real[satker_col] == satker_jalan]
            df_real_agg_filtered = df_real_agg[df_real_agg[satker_col] == satker_jalan]
            df_ren_swa_filtered = df_ren_swa[df_ren_swa[satker_col] == satker_jalan]
            df_real_swa_filtered = df_real_swa[df_real_swa[satker_col] == satker_jalan]
            satker_loop_list = [satker_jalan]

        # Logika Inti Paket Tidak Terealisasi (DIKUNCI: Hanya mencocokkan perencanaan penyedia vs realisasi penyedia)
        df_tidak_realisasi_master = pd.merge(df_ren_filtered, df_real_agg_filtered[[rup_col, satker_col]], on=[rup_col, satker_col], how='left', indicator=True)
        df_tidak_realisasi = df_tidak_realisasi_master[df_tidak_realisasi_master['_merge'] == 'left_only'].drop(columns=['_merge'])

        # Double-check Proteksi: Buang sisa jika ada anomali metode pengadaan swakelola di dalam draf tidak terealisasi global
        if 'Metode Pengadaan' in df_tidak_realisasi.columns:
            df_tidak_realisasi = df_tidak_realisasi[~df_tidak_realisasi['Metode Pengadaan'].astype(str).str.lower().str.contains('swakelola', na=False)]

        # =====================================================================
        # OPSI 1: LAPORAN KESELURUHAN (MURNI PENYEDIA & MURNI SWAKELOLA)
        # =====================================================================
        if "1. Laporan Keseluruhan" in opsi_jalan:
            st.success(f"📊 Menampilkan Analisis Data untuk: **{satker_jalan}**")
            
            # --- TAMPILAN JALUR 1: MURNI PENYEDIA ---
            st.markdown("### 🔵 JALUR PENYEDIA (E-Katalog, Tokodaring, Tender, dsb)")
            c1, c2, c3, c4 = st.columns(4)
            df_merge_glob = pd.merge(df_ren_filtered[[rup_col, satker_col, val_col]], df_real_agg_filtered[[rup_col, satker_col, val_col]], on=[rup_col, satker_col], how='outer', indicator=True)
            
            # Double check baris right_only agar paket tanpa RUP swakelola tidak masuk ke metrik penyedia
            df_right_murni_penyedia = df_merge_glob[df_merge_glob["_merge"]=="right_only"]
            
            c1.markdown(f'<div class="stat-card"><div class="stat-label">SESUAI RENCANA (PENYEDIA)</div><div class="stat-value">{len(df_merge_glob[df_merge_glob["_merge"]=="both"])} Pkt</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="stat-card" style="border-top: 5px solid #e67e22;"><div class="stat-label">TIDAK TEREALISASI (MURNI PENYEDIA)</div><div class="stat-value" style="color: #e67e22;">{len(df_tidak_realisasi)} Pkt (Rp {df_tidak_realisasi[val_col].sum():,.0f})</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="stat-card" style="border-top: 5px solid #c0392b;"><div class="stat-label">TANPA RUP / TIDAK SESUAI</div><div class="stat-value" style="color: #c0392b;">{len(df_right_murni_penyedia)} Pkt (Rp {df_right_murni_penyedia[val_col + "_y"].sum():,.0f})</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="stat-card"><div class="stat-label">TOTAL REALISASI PENYEDIA</div><div class="stat-value">Rp {df_real_filtered[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)

            # --- TAMPILAN JALUR 2: MURNI SWAKELOLA ---
            st.markdown("### 🟢 JALUR SWAKELOLA (Dikerjakan Mandiri Kelompok/Instansi)")
            s1, s2, s3 = st.columns(3)
            s1.metric("Pagu Swakelola (SIRUP)", f"Rp {df_ren_swa_filtered[val_col].sum():,.0f}", f"{len(df_ren_swa_filtered)} Paket")
            s2.metric("Realisasi Swakelola", f"Rp {df_real_swa_filtered[val_col].sum():,.0f}", f"{len(df_real_swa_filtered)} Paket")
            s3.metric("Selisih/Sisa Anggaran Swakelola", f"Rp {df_ren_swa_filtered[val_col].sum() - df_real_swa_filtered[val_col].sum():,.0f}")
            st.divider()

            # --- PROSES GENERATE TABEL REKAP TERPISAH ---
            rekap_penyedia_list = []
            rekap_swakelola_list = []

            for i, s in enumerate(satker_loop_list, 1):
                # 1. Pengolahan Data Penyedia per Satker
                ren_s = df_ren[df_ren[satker_col] == s]
                real_s = df_real_agg[df_real_agg[satker_col] == s]
                merge_s = pd.merge(ren_s[[rup_col, satker_col, val_col]].rename(columns={val_col: 'Angg_Ren'}), real_s[[rup_col, satker_col, val_col, 'Kat_Audit']].rename(columns={val_col: 'Angg_Real'}), on=[rup_col, satker_col], how='outer', indicator=True)
                
                df_sesuai = merge_s[merge_s['_merge'] == 'both']
                df_tidak_real_s = merge_s[merge_s['_merge'] == 'left_only']
                df_tanpa_rup_s = merge_s[merge_s['_merge'] == 'right_only']
                df_td_s = real_s[real_s['Kat_Audit'] == 'Tokodaring']

                rekap_penyedia_list.append({
                    'No': i, 'Nama Satuan Kerja': s,
                    'Sesuai RUP (Pkt)': len(df_sesuai), 'Sesuai RUP (Angg)': df_sesuai['Angg_Real'].sum(),
                    'Tidak Terealisasi (Pkt)': len(df_tidak_real_s), 'Tidak Terealisasi (Angg)': df_tidak_real_s['Angg_Ren'].sum(),
                    'Tanpa Rencana / Siluman (Pkt)': len(df_tanpa_rup_s), 'Tanpa Rencana / Siluman (Angg)': df_tanpa_rup_s['Angg_Real'].sum(),
                    'Tokodaring (Pkt)': len(df_td_s), 'Tokodaring (Angg)': df_td_s[val_col].sum(),
                    'Total Realisasi Penyedia': real_s[val_col].sum()
                })

                # 2. Pengolahan Data Swakelola per Satker
                ren_s_swa = df_ren_swa[df_ren_swa[satker_col] == s]
                real_s_swa = df_real_swa[df_real_swa[satker_col] == s]
                rekap_swakelola_list.append({
                    'No': i, 'Nama Satuan Kerja': s,
                    'Pagu Swakelola SIRUP (Pkt)': len(ren_s_swa), 'Pagu Swakelola SIRUP (Angg)': ren_s_swa[val_col].sum(),
                    'Realisasi Swakelola (Pkt)': len(real_s_swa), 'Realisasi Swakelola (Angg)': real_s_swa[val_col].sum(),
                    'Selisih Anggaran Swakelola': ren_s_swa[val_col].sum() - real_s_swa[val_col].sum()
                })

            df_final_penyedia = pd.DataFrame(rekap_penyedia_list)
            df_final_swakelola = pd.DataFrame(rekap_swakelola_list)

            # Tampilkan Tabel Penyedia di Web
            st.subheader("📑 1. Tabel Rekapitulasi Murni Jalur Penyedia")
            st.dataframe(df_final_penyedia.style.format(precision=0, thousands=","), use_container_width=True)
            
            # Tampilkan Tabel Swakelola di Web
            st.subheader("📑 2. Tabel Rekapitulasi Murni Jalur Swakelola")
            st.dataframe(df_final_swakelola.style.format(precision=0, thousands=","), use_container_width=True)

            # --- PANEL DOWNLOAD MASING-MASING DATA (TERPISAH KAKU) ---
            st.markdown("### 🗂️ Unduh Laporan Rekonsiliasi Terpisah:")
            down_col1, down_col2 = st.columns(2)
            
            with down_col1:
                buf_penyedia = io.BytesIO()
                with pd.ExcelWriter(buf_penyedia, engine='xlsxwriter') as w:
                    df_final_penyedia.to_excel(w, sheet_name='REKAP_PENYEDIA', index=False)
                st.download_button(
                    label="📥 Download Excel khusus JALUR PENYEDIA",
                    data=buf_penyedia.getvalue(),
                    file_name=f"Laporan_Murni_Penyedia_{satker_jalan.replace(' ', '_')}.xlsx",
                    use_container_width=True
                )
                
            with down_col2:
                buf_swa = io.BytesIO()
                with pd.ExcelWriter(buf_swa, engine='xlsxwriter') as w:
                    df_final_swakelola.to_excel(w, sheet_name='REKAP_SWAKELOLA', index=False)
                st.download_button(
                    label="📥 Download Excel khusus JALUR SWAKELOLA",
                    data=buf_swa.getvalue(),
                    file_name=f"Laporan_Murni_Swakelola_{satker_jalan.replace(' ', '_')}.xlsx",
                    use_container_width=True
                )

        # =====================================================================
        # OPSI 2 & 3: REPORT DETAIL
        # =====================================================================
        elif "2. Laporan Paket Tidak Terealisasi" in opsi_jalan:
            st.warning(f"📋 Detail Paket Penyedia **Tidak Terealisasi** untuk: **{satker_jalan}**")
            st.metric("Total Gagal Realisasi (Murni Penyedia)", f"Rp {df_tidak_realisasi[val_col].sum():,.0f}", f"{len(df_tidak_realisasi)} Paket")
            search = st.text_input("🔍 Cari nama paket:")
            nama_paket_col = 'Nama Paket' if 'Nama Paket' in df_tidak_realisasi.columns else df_tidak_realisasi.columns[0]
            df_display = df_tidak_realisasi[df_tidak_realisasi[nama_paket_col].astype(str).str.contains(search, case=False, na=False)] if search else df_tidak_realisasi
            st.dataframe(df_display[[satker_col, rup_col, nama_paket_col, val_col]].style.format({val_col: "{:,.0f}"}), use_container_width=True)

        elif "3. Laporan Khusus Toko Daring" in opsi_jalan:
            st.info(f"🛒 Transaksi **Toko Daring** untuk: **{satker_jalan}**")
            df_tokodaring = df_real_filtered[df_real_filtered['Kat_Audit'] == 'Tokodaring']
            st.metric("Total Transaksi", f"Rp {df_tokodaring[val_col].sum():,.0f}", f"{len(df_tokodaring)} Paket")
            nama_paket_col = 'Nama Paket' if 'Nama Paket' in df_tokodaring.columns else df_tokodaring.columns[0]
            st.dataframe(df_tokodaring[[satker_col, rup_col, nama_paket_col, val_col]].style.format({val_col: "{:,.0f}"}), use_container_width=True)
    else:
        st.warning("⚠️ Tentukan OPD dan Jenis Analisis di atas, lalu klik **🚀 Proses Data**.")
else:
    st.info("👋 Selamat Datang! Silakan unggah data SIRUP dan Realisasi pada sidebar.")
