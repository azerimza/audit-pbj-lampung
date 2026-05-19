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

    # --- FITUR FILTER PER INSTANSI / SATKER ---
    st.title("📊 Dashboard Audit & Rekonsiliasi")
    
    list_satker_pilihan = ["Semua Satker"] + sorted(df_ren[satker_col].dropna().unique().tolist())
    satker_terpilih = st.selectbox("🔍 Pilih Instansi / Satuan Kerja:", list_satker_pilihan)

    # Filter data berdasarkan pilihan user sebelum masuk ke tampilan
    if satker_terpilih == "Semua Satker":
        df_ren_filtered = df_ren
        df_real_filtered = df_real
        df_real_agg_filtered = df_real_agg
        satker_loop_list = sorted(df_ren[satker_col].dropna().unique())
    else:
        df_ren_filtered = df_ren[df_ren[satker_col] == satker_terpilih]
        df_real_filtered = df_real[df_real[satker_col] == satker_terpilih]
        df_real_agg_filtered = df_real_agg[df_real_agg[satker_col] == satker_terpilih]
        satker_loop_list = [satker_terpilih]

    # --- LOGIKA IDENTIFIKASI TIDAK TEREALISASI ---
    # Merge untuk mencari apa yang ada di perencanaan tapi tidak ada di realisasi (left_only)
    df_tidak_realisasi_master = pd.merge(df_ren_filtered, df_real_agg_filtered[[rup_col]], on=rup_col, how='left', indicator=True)
    df_tidak_realisasi = df_tidak_realisasi_master[df_tidak_realisasi_master['_merge'] == 'left_only'].drop(columns=['_merge'])

    # Hitung metrik total tidak terealisasi
    total_pkt_tidak_realisasi = len(df_tidak_realisasi)
    total_anggaran_tidak_realisasi = df_tidak_realisasi[val_col].sum()

    # --- 4. TAMPILAN DASHBOARD (DENGAN DATA FILTERED) ---
    c1, c2, c3, c4 = st.columns(4)
    df_merge_glob = pd.merge(df_ren_filtered[[rup_col, val_col]], df_real_agg_filtered[[rup_col, val_col]], on=rup_col, how='right', indicator=True)
    
    c1.markdown(f'<div class="stat-card"><div class="stat-label">SESUAI RENCANA</div><div class="stat-value">{len(df_merge_glob[df_merge_glob["_merge"]=="both"])} Pkt</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-card"><div class="stat-label">TANPA RENCANA</div><div class="stat-value">{len(df_merge_glob[df_merge_glob["_merge"]=="right_only"])} Pkt</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-card"><div class="stat-label">TOTAL REALISASI</div><div class="stat-value">Rp {df_real_filtered[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-card"><div class="stat-label">EFISIENSI ANGGARAN</div><div class="stat-value">Rp {df_ren_filtered[val_col].sum() - df_real_filtered[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)

    # --- FITUR BARU: RINGKASAN TIDAK TEREALISASI ---
    st.divider()
    st.subheader(f"❌ Ringkasan Paket Tidak Terealisasi ({satker_terpilih})")
    
    mc1, mc2 = st.columns(2)
    with mc1:
        st.metric(label="Jumlah Paket Tidak Terealisasi", value=f"{total_pkt_tidak_realisasi} Paket")
    with mc2:
        st.metric(label="Total Anggaran Tidak Terealisasi", value=f"Rp {total_anggaran_tidak_realisasi:,.0f}")

    # --- TAB DETAIL PENCARIAN PAKET TIDAK TEREALISASI ---
    search_keyword = st.text_input("🔍 Cari Paket Tidak Terealisasi (Masukkan Nama Paket / Nama Satker / Metode):")
    
    # Deteksi kolom nama paket (menghindari error jika nama kolom berbeda di CSV Mas)
    nama_paket_col = 'Nama Paket' if 'Nama Paket' in df_tidak_realisasi.columns else (df_tidak_realisasi.columns[2] if len(df_tidak_realisasi.columns) > 2 else df_tidak_realisasi.columns[0])
    
    # Jalankan filter pencarian jika user mengetik sesuatu
    if search_keyword:
        df_tidak_realisasi_display = df_tidak_realisasi[
            df_tidak_realisasi[nama_paket_col].astype(str).str.contains(search_keyword, case=False, na=False) |
            df_tidak_realisasi[satker_col].astype(str).str.contains(search_keyword, case=False, na=False)
        ]
    else:
        df_tidak_realisasi_display = df_tidak_realisasi

    # Tampilkan tabel detail paket tidak terealisasi
    if not df_tidak_realisasi_display.empty:
        st.caption(f"Menampilkan {len(df_tidak_realisasi_display)} paket yang tidak terealisasi")
        # Pilih beberapa kolom penting saja agar tabel rapi di layar
        kolom_tampil = [satker_col, rup_col, nama_paket_col, val_col]
        # Pastikan kolom_tampil ada di dataframe
        kolom_tampil = [col for col in kolom_tampil if col in df_tidak_realisasi_display.columns]
        
        st.dataframe(df_tidak_realisasi_display[kolom_tampil].style.format({val_col: "{:,.0f}"}), use_container_width=True)
        
        # Tombol download khusus data tidak terealisasi
        buffer_tr = io.BytesIO()
        with pd.ExcelWriter(buffer_tr, engine='xlsxwriter') as writer:
            df_tidak_realisasi_display.to_excel(writer, sheet_name='Tidak_Terealisasi', index=False)
        st.download_button(f"📥 Download Data Tidak Terealisasi ({satker_terpilih})", buffer_tr.getvalue(), f"Tidak_Terealisasi_{satker_terpilih.replace(' ', '_')}.xlsx")
    else:
        st.info("Tidak ada paket tidak terealisasi yang cocok dengan pencarian.")

    # --- 5. TABEL LAPORAN UTAMA (REKAP PER SATKER) ---
    st.divider()
    st.subheader(f"📑 Laporan Audit Rekonsiliasi Keseluruhan - {satker_terpilih}")
    
    rekap_list = []
    
    for i, s in enumerate(satker_loop_list, 1):
        ren_s = df_ren[df_ren[satker_col] == s]
        real_s = df_real_agg[df_real_agg[satker_col] == s]
        
        merge_s = pd.merge(ren_s[[rup_col, val_col]], real_s[[rup_col, val_col, 'Kat_Audit']], on=rup_col, how='right', indicator=True)
        
        sesuai_rup_df = merge_s[merge_s['_merge'] == 'both']
        tidak_sesuai_df = merge_s[merge_s['_merge'] == 'right_only']
        
        tokodaring_s = real_s[real_s['Kat_Audit'] == 'Tokodaring']
        swakelola_real_s = real_s[real_s['Kat_Audit'] == 'Swakelola']

        rekap_list.append({
            'No': i, 
            'Nama Satuan Kerja': s,
            'Sesuai RUP (Pkt)': len(sesuai_rup_df),
            'Sesuai RUP (Angg)': sesuai_rup_df[val_col + '_y'].sum(),
            'Swakelola Realisasi (Pkt)': len(swakelola_real_s),
            'Swakelola Realisasi (Angg)': swakelola_real_s[val_col].sum(),
            'Tokodaring (Pkt)': len(tokodaring_s),
            'Tokodaring (Angg)': tokodaring_s[val_col].sum(),
            'Tidak Sesuai RUP (Pkt)': len(tidak_sesuai_df),
            'Tidak Sesuai RUP (Angg)': tidak_sesuai_df[val_col + '_y'].sum(),
            'Selisih Anggaran': ren_s[val_col].sum() - real_s[val_col].sum(),
            'Identifikasi': "Overbudget" if (sesuai_rup_df[val_col + '_y'] > sesuai_rup_df[val_col + '_x']).any() else "Normal"
        })

    df_final = pd.DataFrame(rekap_list)
    st.dataframe(df_final.style.format(precision=0, thousands=","), use_container_width=True)

    # --- 6. EXPORT ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, sheet_name='Laporan_Audit', index=False)
    st.download_button(f"📥 Download Laporan Utama {satker_terpilih}", buffer.getvalue(), f"Laporan_Audit_{satker_terpilih.replace(' ', '_')}.xlsx")

else:
    st.info("👋 Selamat Datang! Silakan unggah data SIRUP dan Realisasi pada sidebar.")
