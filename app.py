import streamlit as st
import pandas as pd
import numpy as np
import io

# --- 1. CONFIG ---
st.set_page_config(page_title="Audit Rekonsiliasi PBJ", layout="wide")

@st.cache_data
def read_csv(file):
    try:
        return pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
    except:
        return pd.read_csv(file, sep=None, engine='python', encoding='cp1252')

def clean_val(df, col):
    if col in df.columns:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)
    return df

# --- 2. SIDEBAR ---
with st.sidebar:
    st.title("Audit Lab")
    file_ren = st.file_uploader("Upload SIRUP (Rencana)", type=['csv'])
    file_real = st.file_uploader("Upload Realisasi", type=['csv'])

if file_ren and file_real:
    df_ren = read_csv(file_ren)
    df_real = read_csv(file_real)
    
    # Cleaning Columns
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()
    
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'
    metode_col = 'Metode Pengadaan' # Atau 'Sumber Transaksi'
    satker_col = 'Nama Satuan Kerja'
    jenis_col = 'Jenis Pengadaan' # Untuk membedakan Swakelola/Penyedia

    df_ren = clean_val(df_ren, val_col)
    df_real = clean_val(df_real, val_col)

    # --- LOGIKA 1 & 2: AGREGASI REALISASI (GROUPING BY RUP) ---
    # Kita jumlahkan anggaran realisasi per Kode RUP agar unik
    df_real_unique = df_real.groupby(rup_col).agg({
        val_col: 'sum',
        satker_col: 'first',
        metode_col: 'first',
        jenis_col: 'first'
    }).reset_index()

    # --- MAPPING & MERGING ---
    df_merge = pd.merge(
        df_ren[[rup_col, val_col, satker_col, jenis_col]].rename(columns={val_col: 'Pagu_Rencana'}),
        df_real_unique[[rup_col, val_col, metode_col]].rename(columns={val_col: 'Total_Realisasi'}),
        on=rup_col,
        how='outer',
        indicator=True
    )

    # --- LOGIKA 1, 2, 3 (IDENTIFIKASI) ---
    # 1. Sesuai Rencana (Ada di keduanya)
    df_sesuai = df_merge[df_merge['_merge'] == 'both']
    
    # 2. Hanya di Realisasi (Tidak ada di SIRUP)
    df_extra = df_merge[df_merge['_merge'] == 'right_only']
    
    # 3. Melebihi Anggaran (Overbudget)
    df_over = df_sesuai[df_sesuai['Total_Realisasi'] > df_sesuai['Pagu_Rencana']]

    # --- LOGIKA 4: PEMISAHAN SPESIFIK ---
    def kategori_pbj(row):
        m = str(row[metode_col]).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Toko Daring'
        if 'katalog 5' in m: return 'E-Katalog 5.0'
        if 'katalog 6' in m: return 'E-Katalog 6.0'
        if 'pencatatan' in m and 'simpel' not in m: return 'Pencatatan'
        if 'simpelpencatatan' in m: return 'SimpelPencatatan'
        if 'non tender' in m: return 'Non Tender'
        if 'swakelola' in m: return 'Swakelola'
        return 'Lainnya'

    df_real_unique['Kategori_Audit'] = df_real_unique.apply(kategori_pbj, axis=1)

    # --- LOGIKA 5: LAPORAN TABULAR (REKAP SATKER) ---
    st.header("📑 Laporan Audit Rekonsiliasi Satker")
    
    satkers = sorted(df_ren[satker_col].dropna().unique())
    rekap_data = []

    for s in satkers:
        # Filter data per satker
        r_ren = df_ren[df_ren[satker_col] == s]
        r_real = df_real_unique[df_real_unique[satker_col] == s]
        r_merge = df_merge[df_merge[satker_col] == s]

        # RUP Perencanaan
        swakelola_ren = r_ren[r_ren[jenis_col].str.contains('Swakelola', na=False)]
        penyedia_ren = r_ren[~r_ren[jenis_col].str.contains('Swakelola', na=False)]

        # Realisasi
        swakelola_real = r_real[r_real['Kategori_Audit'] == 'Swakelola']
        
        # Penyedia Detail
        penyedia_match = r_merge[r_merge['_merge'] == 'both']
        penyedia_no_match = r_merge[r_merge['_merge'] == 'right_only']
        penyedia_tokodaring = r_real[r_real['Kategori_Audit'] == 'Toko Daring']

        rekap_data.append({
            'Nama Satuan Kerja': s,
            'RUP Swakelola (Pkt)': len(swakelola_ren),
            'RUP Swakelola (Angg)': swakelola_ren['Pagu_Rencana'].sum() if 'Pagu_Rencana' in swakelola_ren else 0,
            'RUP Penyedia (Pkt)': len(penyedia_ren),
            'RUP Penyedia (Angg)': penyedia_ren['Pagu_Rencana'].sum() if 'Pagu_Rencana' in penyedia_ren else 0,
            'Real Swakelola (Angg)': swakelola_real[val_col].sum(),
            'Penyedia (Sesuai RUP)': penyedia_match['Total_Realisasi'].sum(),
            'Penyedia (Tidak Sesuai)': penyedia_no_match['Total_Realisasi'].sum(),
            'Penyedia (Toko Daring)': penyedia_tokodaring[val_col].sum(),
            'Selisih Anggaran': (r_ren[val_col].sum() - r_real[val_col].sum())
        })

    df_laporan_final = pd.DataFrame(rekap_data)
    st.dataframe(df_laporan_final.style.format(precision=0, thousands=","), use_container_width=True)

    # Tombol Download
    output = io.BytesIO()
    df_laporan_final.to_excel(output, index=False)
    st.download_button("📥 Download Laporan Audit Satker (.xlsx)", output.getvalue(), "Laporan_Audit_Detail.xlsx")

    # --- VISUALISASI KATEGORI (POIN 4) ---
    st.divider()
    st.subheader("📊 Distribusi Kategori Realisasi (Poin 4)")
    summary_kategori = df_real_unique.groupby('Kategori_Audit').agg({val_col: 'sum', rup_col: 'count'}).rename(columns={rup_col: 'Jumlah Paket'})
    st.table(summary_kategori.style.format(precision=0, thousands=","))

else:
    st.info("Silakan unggah kedua file CSV untuk memproses audit rekonsiliasi.")
