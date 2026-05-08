import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Audit PBJ Lampung v6.2", layout="wide")

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
    st.title("Audit PBJ v6.2")
    st.markdown("**Reza Saputra Azmi**")
    file_ren = st.file_uploader("Upload Data SIRUP (Rencana)", type=['csv'])
    file_real = st.file_uploader("Upload Data Realisasi", type=['csv'])

# --- 3. ENGINE UTAMA ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    
    # Cleaning & Format Angka
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'
    metode_col = 'Metode Pengadaan'
    satker_col = 'Nama Satuan Kerja'
    
    for df in [df_ren, df_real]:
        df.columns = df.columns.str.strip()
        df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # AGREGASI REALISASI (Logika Poin 1 & 2: Grouping by RUP)
    df_real_agg = df_real.groupby(rup_col).agg({
        val_col: 'sum',
        satker_col: 'first',
        metode_col: 'first',
        'Jenis Pengadaan': 'first'
    }).reset_index()

    # MAPPING KATEGORI (Logika Poin 4)
    def get_kategori(row):
        m = str(row[metode_col]).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Toko Daring'
        if 'katalog 5' in m: return 'E-Katalog 5.0'
        if 'katalog 6' in m: return 'E-Katalog 6.0'
        if 'simpelpencatatan' in m: return 'SimpelPencatatan'
        if 'pencatatan' in m: return 'Pencatatan'
        if 'non tender' in m: return 'Non Tender'
        if 'swakelola' in m: return 'Swakelola'
        return 'Lainnya'

    df_real_agg['Kategori_Audit'] = df_real_agg.apply(get_kategori, axis=1)

    # MERGE UNTUK REKONSILIASI (Poin 1, 2, 3)
    df_merge = pd.merge(
        df_ren[[rup_col, val_col, satker_col, 'Jenis Pengadaan']].rename(columns={val_col: 'Pagu_SIRUP'}),
        df_real_agg[[rup_col, val_col, 'Kategori_Audit']].rename(columns={val_col: 'Total_Realisasi'}),
        on=rup_col, how='outer', indicator=True
    )

    # --- 4. EXPORT ENGINE (FIXED) ---
    st.subheader("📥 Ekspor Laporan")
    
    # Menyiapkan buffer untuk Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Sheet 1: Ringkasan Audit
        summary_stats = pd.DataFrame({
            'Indikator Audit': ['Total Pagu Rencana', 'Total Realisasi', 'Selisih (Efisiensi)'],
            'Nilai (Rp)': [df_ren[val_col].sum(), df_real[val_col].sum(), df_ren[val_col].sum() - df_real[val_col].sum()]
        })
        summary_stats.to_excel(writer, sheet_name='Ringkasan', index=False)
        
        # Sheet 2: Data Rekonsiliasi (Poin 1, 2, 3)
        df_merge.to_excel(writer, sheet_name='Rekonsiliasi_RUP', index=False)
        
        # Sheet 3: Kategori Transaksi (Poin 4)
        df_real_agg.to_excel(writer, sheet_name='Detail_Kategori', index=False)
        
        # Format Excel agar rapi
        workbook = writer.book
        num_format = workbook.add_format({'num_format': '#,##0'})
        for sheet in writer.sheets.values():
            sheet.set_column('B:E', 18, num_format)

    st.download_button(
        label="✅ Download Laporan Excel (v6.2)",
        data=buffer.getvalue(),
        file_name=f"Audit_PBJ_Lampung_{datetime.now().strftime('%d%m%y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- 5. TAMPILAN DASHBOARD (Logika Tetap) ---
    st.divider()
    st.markdown("### 📊 Ringkasan Realisasi")
    col1, col2 = st.columns(2)
    col1.metric("Total Pagu SIRUP", f"Rp {df_ren[val_col].sum():,.0f}")
    col2.metric("Total Realisasi", f"Rp {df_real[val_col].sum():,.0f}")

else:
    st.info("Silakan unggah data SIRUP dan Realisasi untuk memulai.")
