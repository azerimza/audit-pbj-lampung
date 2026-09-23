import streamlit as st
import pandas as pd
import io

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Audit PBJ Lampung",
    page_icon="📊",
    layout="wide"
)

# ==============================================================================
# 1. FUNGSI UTILITAS & PENDUKUNG
# ==============================================================================
def add_index(df):
    if df is not None and len(df) > 0:
        df_copy = df.copy()
        if 'No' not in df_copy.columns:
            df_copy.insert(0, 'No', range(1, len(df_copy) + 1))
        return df_copy
    return df

# Dummy / placeholder dataframes untuk simulasi struktur aplikasi
# (Ganti atau sesuaikan bagian pemuatan data asli Anda di sini jika diperlukan)
@st.cache_data
def load_data():
    # Contoh inisialisasi dataframe kosong/dummy agar aplikasi dapat berjalan
    df_laporan = pd.DataFrame({'Kategori': ['A', 'B'], 'Pagu': [1000000, 2000000], 'Realisasi': [800000, 1500000], 'Selisih': [200000, 500000], 'Persentase': [0.8, 0.75]})
    df_sanding_view = pd.DataFrame()
    df_sesuai = pd.DataFrame()
    df_real_only = pd.DataFrame()
    df_belum_teralisasi = pd.DataFrame()
    df_ekatalog = pd.DataFrame()
    df_tokodaring = pd.DataFrame()
    return df_laporan, df_sanding_view, df_sesuai, df_real_only, df_belum_teralisasi, df_ekatalog, df_tokodaring

df_laporan, df_sanding_view, df_sesuai, df_real_only, df_belum_teralisasi, df_ekatalog, df_tokodaring = load_data()

# ==============================================================================
# 2. SIDEBAR & NAVIGASI
# ==============================================================================
st.sidebar.title("Navigasi Audit PBJ")
satker_terpilih = st.sidebar.selectbox("Pilih Satuan Kerja / OPD", ["Semua OPD", "Dinas Pendidikan", "Dinas Kesehatan", "PUPR"])

st.title("Dashboard Audit Pengadaan Barang dan Jasa (PBJ)")
st.markdown("---")

# ==============================================================================
# 3. KONTEN UTAMA APLIKASI
# ==============================================================================
st.subheader("Ringkasan Eksekutif")
st.dataframe(df_laporan, use_container_width=True)

# ==============================================================================
# 4. ENGINE FILE EXPORT EXCEL (VERSI DIPERBAIKI / FULL)
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
                # Memastikan data numerik aman dari tipe data kosong/null
                for c_idx in range(1, 4):
                    val = df_sum.iloc[row, c_idx]
                    num_v = pd.to_numeric(val, errors='coerce')
                    ws.write(row+5, c_idx, num_v if pd.notnull(num_v) else 0, curr_fmt)
                
                val_pct = df_sum.iloc[row, 4]
                num_pct = pd.to_numeric(val_pct, errors='coerce')
                ws.write(row+5, 4, num_pct if pd.notnull(num_pct) else 0, pct_fmt)

        for name, df_d in dict_detail.items():
            if df_d is not None and len(df_d) > 0:
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
                            
                            val_pagu = pd.to_numeric(row_data.get('Pagu Rencana (SIRUP)', 0), errors='coerce')
                            ws_s.write(excel_row, 4, val_pagu if pd.notnull(val_pagu) else 0, curr_fmt)
                            last_rup = current_rup
                        else:
                            idx_realisasi += 1
                            for c_left in range(5):
                                ws_s.write(excel_row, c_left, '', text_fmt)
                                
                        ws_s.write(excel_row, 7, idx_realisasi, text_fmt)
                        ws_s.write(excel_row, 8, str(row_data.get('Nama Penyedia (Realisasi)', '')), text_fmt)
                        
                        val_riil = pd.to_numeric(row_data.get('Nilai Riil Realisasi', 0), errors='coerce')
                        ws_s.write(excel_row, 9, val_riil if pd.notnull(val_riil) else 0, curr_fmt)
                        
                        val_selisih = pd.to_numeric(row_data.get('Selisih Transaksi (Rp)', 0), errors='coerce')
                        ws_s.write(excel_row, 10, val_selisih if pd.notnull(val_selisih) else 0, curr_fmt)
                        
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
                                num_val = pd.to_numeric(val, errors='coerce')
                                ws_d.write(r_idx+1, c_idx, num_val if pd.notnull(num_val) else 0, curr_fmt)
                            else:
                                ws_d.write(r_idx+1, c_idx, str(val) if pd.notnull(val) else '', text_fmt)
                                
                    ws_d.set_column(0, 0, 6)
                    ws_d.set_column(1, len(df_idx.columns)-1, 24)
    return out.getvalue()

# Tombol Download di antarmuka Streamlit
excel_data = generate_excel(df_laporan, dict_all_data, satker_terpilih)
st.download_button(
    label="📥 Unduh Master Laporan Excel",
    data=excel_data,
    file_name=f"Laporan_Audit_PBJ_{satker_terpilih.replace(' ', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
