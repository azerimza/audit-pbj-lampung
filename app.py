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
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col, rup_col, satker_col = 'Total Nilai (Rp)', 'Kode RUP', 'Nama Satuan Kerja'
    
    # Bersihkan nama kolom
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    # Paksa Kode RUP jadi String
    df_ren[rup_col] = df_ren[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)
    df_real[rup_col] = df_real[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)

    for df in [df_ren, df_real]:
        if val_col in df.columns:
            df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # PEMISAHAN KATEGORI BERDASARKAN SUMBER TRANSAKSI / METODE
    def map_kat(m):
        m = str(m).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Tokodaring'
        if 'swakelola' in m: return 'Swakelola'
        if 'katalog' in m: return 'E-Katalog'
        return 'Penyedia Lainnya'

    if 'Metode Pengadaan' in df_real.columns:
        df_real['Kat_Audit'] = df_real['Metode Pengadaan'].apply(map_kat)
    else:
        df_real['Kat_Audit'] = 'Lainnya'
    
    df_real_agg = df_real.groupby(rup_col).agg({
        val_col: 'sum', satker_col: 'first', 'Kat_Audit': 'first'
    }).reset_index()

    # --- 4. PANEL FILTER UTAMA ---
    st.title("📊 Dashboard Audit & Rekonsiliasi")
    
    # Grid input untuk OPD dan Pilihan Laporan
    f1, f2, f3 = st.columns([2, 2, 1])
    with f1:
        list_satker_pilihan = ["Semua OPD / Satker"] + sorted(df_ren[satker_col].dropna().unique().tolist())
        satker_terpilih = st.selectbox("🔍 Pilih OPD / Instansi:", list_satker_pilihan)
    with f2:
        opsi_proses = st.selectbox("⚙️ Pilih Jenis Analisis Laporan:", [
            "1. Laporan Keseluruhan (Realisasi & Tidak Terealisasi)",
            "2. Laporan Paket Tidak Terealisasi Saja",
            "3. Laporan Khusus Toko Daring"
        ])
    with f3:
        st.markdown("<br>", unsafe_allow_html=True)
        tombol_proses = st.button("🚀 Proses Data", use_container_width=True)

    # Menyimpan state di latar belakang agar data tidak hilang saat user berinteraksi
    if 'proses_dijalankan' not in st.session_state:
        st.session_state.proses_dijalankan = False
    if 'satker_aktif' not in st.session_state:
        st.session_state.satker_aktif = ""
    if 'opsi_aktif' not in st.session_state:
        st.session_state.opsi_aktif = ""

    # Pemicu klik tombol
    if tombol_proses:
        st.session_state.proses_dijalankan = True
        st.session_state.satker_aktif = satker_terpilih
        st.session_state.opsi_aktif = opsi_proses

    # --- JALANKAN PROSES JIKA TOMBOL DIKLIK ---
    if st.session_state.proses_dijalankan:
        satker_jalan = st.session_state.satker_aktif
        opsi_jalan = st.session_state.opsi_aktif

        # Logika Penentuan Filter OPD
        if satker_jalan == "Semua OPD / Satker":
            df_ren_filtered = df_ren
            df_real_filtered = df_real
            df_real_agg_filtered = df_real_agg
            satker_loop_list = sorted(df_ren[satker_col].dropna().unique())
        else:
            df_ren_filtered = df_ren[df_ren[satker_col] == satker_jalan]
            df_real_filtered = df_real[df_real[satker_col] == satker_jalan]
            df_real_agg_filtered = df_real_agg[df_real_agg[satker_col] == satker_jalan]
            satker_loop_list = [satker_jalan]

        # Logika Inti Analisis Tidak Terealisasi (Ada di Perencanaan, tidak ada di Realisasi)
        df_tidak_realisasi_master = pd.merge(df_ren_filtered, df_real_agg_filtered[[rup_col]], on=rup_col, how='left', indicator=True)
        df_tidak_realisasi = df_tidak_realisasi_master[df_tidak_realisasi_master['_merge'] == 'left_only'].drop(columns=['_merge'])

        # =====================================================================
        # OPSI 1: LAPORAN KESELURUHAN (OPSIONAL PER OPD)
        # =====================================================================
        if "1. Laporan Keseluruhan" in opsi_jalan:
            st.success(f"📊 Menampilkan **Laporan Keseluruhan** untuk: **{satker_jalan}**")
            
            # Kartu Ringkasan Atas
            c1, c2, c3, c4 = st.columns(4)
            df_merge_glob = pd.merge(df_ren_filtered[[rup_col, val_col]], df_real_agg_filtered[[rup_col, val_col]], on=rup_col, how='right', indicator=True)
            
            c1.markdown(f'<div class="stat-card"><div class="stat-label">SESUAI RENCANA</div><div class="stat-value">{len(df_merge_glob[df_merge_glob["_merge"]=="both"])} Pkt</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="stat-card" style="border-top: 5px solid #e67e22;"><div class="stat-label">TIDAK TEREALISASI</div><div class="stat-value" style="color: #e67e22;">{len(df_tidak_realisasi)} Pkt (Rp {df_tidak_realisasi[val_col].sum():,.0f})</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="stat-card"><div class="stat-label">TOTAL REALISASI</div><div class="stat-value">Rp {df_real_filtered[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="stat-card"><div class="stat-label">EFISIENSI ANGGARAN</div><div class="stat-value">Rp {df_ren_filtered[val_col].sum() - df_real_filtered[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)

            # Tabel Rekap Gabungan Per OPD
            rekap_list = []
            for i, s in enumerate(satker_loop_list, 1):
                ren_s = df_ren[df_ren[satker_col] == s]
                real_s = df_real_agg[df_real_agg[satker_col] == s]
                merge_s = pd.merge(ren_s[[rup_col, val_col]], real_s[[rup_col, val_col, 'Kat_Audit']], on=rup_col, how='right', indicator=True)
                
                # Filter tidak terealisasi khusus satker iterasi saat ini
                tr_s = pd.merge(ren_s, real_s[[rup_col]], on=rup_col, how='left', indicator=True)
                tr_s_df = tr_s[tr_s['_merge'] == 'left_only']

                rekap_list.append({
                    'No': i, 
                    'Nama Satuan Kerja': s,
                    'Sesuai RUP (Pkt)': len(merge_s[merge_s['_merge'] == 'both']), 
                    'Sesuai RUP (Angg)': merge_s[merge_s['_merge'] == 'both'][val_col + '_y'].sum(),
                    'Tidak Terealisasi (Pkt)': len(tr_s_df), 
                    'Tidak Terealisasi (Angg)': tr_s_df[val_col].sum(),
                    'Tokodaring (Pkt)': len(real_s[real_s['Kat_Audit'] == 'Tokodaring']), 
                    'Tokodaring (Angg)': real_s[real_s['Kat_Audit'] == 'Tokodaring'][val_col].sum(),
                    'Total Realisasi (Angg)': real_s[val_col].sum()
                })

            df_final = pd.DataFrame(rekap_list)
            st.dataframe(df_final.style.format(precision=0, thousands=","), use_container_width=True)

            # Ekspor Laporan
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, sheet_name='Laporan_Keseluruhan', index=False)
            st.download_button(f"📥 Download Laporan Keseluruhan ({satker_jalan})", buffer.getvalue(), f"Laporan_Keseluruhan_{satker_jalan.replace(' ', '_')}.xlsx")

        # =====================================================================
        # OPSI 2: LAPORAN PAKET TIDAK TEREALISASI SAJA (OPSIONAL PER OPD)
        # =====================================================================
        elif "2. Laporan Paket Tidak Terealisasi" in opsi_jalan:
            st.warning(f"📋 Menampilkan Daftar Detail Paket **Tidak Terealisasi** untuk: **{satker_jalan}**")
            
            # Tampilkan Ringkasan Anggaran yang Hilang/Gagal Realisasi
            st.metric("Total Anggaran Gagal Realisasi", f"Rp {df_tidak_realisasi[val_col].sum():,.0f}", f"{len(df_tidak_realisasi)} Paket")
            
            # Kolom Pencarian Teks
            search = st.text_input("🔍 Cari paket berdasarkan kata kunci nama paket:")
            nama_paket_col = 'Nama Paket' if 'Nama Paket' in df_tidak_realisasi.columns else df_tidak_realisasi.columns[0]
            
            if search:
                df_display = df_tidak_realisasi[df_tidak_realisasi[nama_paket_col].astype(str).str.contains(search, case=False, na=False)]
            else:
                df_display = df_tidak_realisasi

            kolom_tampil = [satker_col, rup_col, nama_paket_col, val_col]
            kolom_tampil = [c for c in kolom_tampil if c in df_display.columns]
            st.dataframe(df_display[kolom_tampil].style.format({val_col: "{:,.0f}"}), use_container_width=True)

            # Ekspor File
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_display.to_excel(writer, sheet_name='Tidak_Terealisasi', index=False)
            st.download_button(f"📥 Download Paket Tidak Terealisasi ({satker_jalan})", buffer.getvalue(), f"Tidak_Terealisasi_{satker_jalan.replace(' ', '_')}.xlsx")

        # =====================================================================
        # OPSI 3: LAPORAN KHUSUS TOKO DARING
        # =====================================================================
        elif "3. Laporan Khusus Toko Daring" in opsi_jalan:
            st.info(f"🛒 Menampilkan Analisis Transaksi **Toko Daring** untuk: **{satker_jalan}**")
            
            df_tokodaring = df_real_filtered[df_real_filtered['Kat_Audit'] == 'Tokodaring']
            st.metric("Total Transaksi Tokodaring", f"Rp {df_tokodaring[val_col].sum():,.0f}", f"{len(df_tokodaring)} Paket")
            
            nama_paket_col = 'Nama Paket' if 'Nama Paket' in df_tokodaring.columns else df_tokodaring.columns[0]
            st.dataframe(df_tokodaring[[satker_col, rup_col, nama_paket_col, val_col]], use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_tokodaring.to_excel(writer, sheet_name='Data_Tokodaring', index=False)
            st.download_button(f"📥 Download Data Tokodaring ({satker_jalan})", buffer.getvalue(), f"Tokodaring_{satker_jalan.replace(' ', '_')}.xlsx")

    else:
        st.warning("⚠️ Tentukan OPD dan Jenis Analisis di atas, lalu klik **🚀 Proses Data**.")
else:
    st.info("👋 Selamat Datang! Silakan unggah data SIRUP dan Realisasi pada sidebar.")
