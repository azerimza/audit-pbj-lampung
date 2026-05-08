import streamlit as st
import pandas as pd
import io

# --- 1. KONDISI VISUAL AWAL (DIKUNCI) ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .metric-card {
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 10px solid #0c2461; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-label { font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
    .metric-value { font-size: 28px; color: #0c2461; font-weight: bold; font-family: 'Consolas', monospace; }
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
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=50)
    st.title("Audit PBJ")
    st.markdown("**Reza Saputra Azmi**")
    file_ren = st.file_uploader("Upload SIRUP", type=['csv'])
    file_real = st.file_uploader("Upload Realisasi", type=['csv'])

if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col, rup_col, satker_col = 'Total Nilai (Rp)', 'Kode RUP', 'Nama Satuan Kerja'
    
    for df in [df_ren, df_real]:
        df.columns = df.columns.str.strip()
        df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # --- POIN 1, 2, 4: AGREGASI & KATEGORISASI ---
    def map_kat(m):
        m = str(m).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Tokodaring'
        if 'katalog 5' in m: return 'E-Katalog 5.0'
        if 'katalog 6' in m: return 'E-Katalog 6.0'
        if 'simpelpencatatan' in m: return 'SimpelPencatatan'
        if 'pencatatan' in m: return 'Pencatatan'
        if 'non tender' in m: return 'Non Tender'
        if 'swakelola' in m: return 'Swakelola'
        return 'Lainnya'

    df_real['Kat_Audit'] = df_real['Metode Pengadaan'].apply(map_kat)
    
    # Agregasi Realisasi: Kode RUP berulang dikondisikan jadi 1 kode & jumlahkan anggaran
    df_real_agg = df_real.groupby(rup_col).agg({
        val_col: 'sum', satker_col: 'first', 'Kat_Audit': 'first', 'Jenis Pengadaan': 'first'
    }).reset_index()

    # --- POIN 5: STRUKTUR LAPORAN REKONSILIASI ---
    rekap_list = []
    for i, s in enumerate(sorted(df_ren[satker_col].dropna().unique()), 1):
        ren_s = df_ren[df_ren[satker_col] == s]
        real_s = df_real_agg[df_real_agg[satker_col] == s]
        
        # RUP Perencanaan
        sw_ren = ren_s[ren_s['Jenis Pengadaan'].str.contains('Swakelola', na=False)]
        py_ren = ren_s[~ren_s['Jenis Pengadaan'].str.contains('Swakelola', na=False)]
        
        # Realisasi Rekonsiliasi (Merge)
        merge_s = pd.merge(ren_s[[rup_col, val_col]], real_s[[rup_col, val_col, 'Kat_Audit']], on=rup_col, how='right', indicator=True)
        
        # Identifikasi Kondisi
        sesuai_rup = merge_s[(merge_s['_merge'] == 'both') & (merge_s['Kat_Audit'] != 'Tokodaring')]
        tidak_sesuai = merge_s[merge_s['_merge'] == 'right_only']
        over_budget = sesuai_rup[sesuai_rup[val_col + '_y'] > sesuai_rup[val_col + '_x']] # POIN 3
        
        rekap_list.append({
            'No': i,
            'Satuan Kerja': s,
            'RUP Swakelola (Pkt)': len(sw_ren),
            'RUP Swakelola (Angg)': sw_ren[val_col].sum(),
            'RUP Penyedia (Pkt)': len(py_ren),
            'RUP Penyedia (Angg)': py_ren[val_col].sum(),
            'Real Swakelola (Angg)': real_s[real_s['Kat_Audit'] == 'Swakelola'][val_col].sum(),
            'Penyedia Sesuai RUP (Angg)': sesuai_rup[val_col + '_y'].sum(),
            'Penyedia Tidak Sesuai RUP (Angg)': tidak_sesuai[val_col + '_y'].sum(),
            'Penyedia Toko Daring (Angg)': real_s[real_s['Kat_Audit'] == 'Tokodaring'][val_col].sum(),
            'Selisih Anggaran': ren_s[val_col].sum() - real_s[val_col].sum(),
            'Keterangan': f"Overbudget: {len(over_budget)} pkt" if len(over_budget) > 0 else "Normal"
        })

    df_laporan = pd.DataFrame(rekap_list)

    # --- TAMPILAN DASHBOARD (VISUAL AWAL) ---
    st.markdown("# ⚖️ Laporan Realisasi Anggaran Detail")
    st.markdown(f'<div class="metric-card"><div class="metric-label">TOTAL PAGU RENCANA</div><div class="metric-value">Rp {df_ren[val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-card" style="border-left-color: #007bff;"><div class="metric-label">REALISASI KATALOG & LAINNYA</div><div class="metric-value">Rp {df_real_agg[df_real_agg["Kat_Audit"].str.contains("Katalog|Pencatatan")][val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-card" style="border-left-color: #ff9900;"><div class="metric-label">REALISASI TOKODARING</div><div class="metric-value">Rp {df_real_agg[df_real_agg["Kat_Audit"] == "Tokodaring"][val_col].sum():,.0f}</div></div>', unsafe_allow_html=True)

    # --- TABEL LAPORAN (POIN 5) ---
    st.divider()
    st.subheader("📑 Tabel Laporan Audit Lengkap (Poin 5)")
    st.dataframe(df_laporan.style.format(precision=0, thousands=","), use_container_width=True)

    # EKSPOR EXCEL
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_laporan.to_excel(writer, sheet_name='Laporan_Audit', index=False)
    st.download_button("📥 Download Excel Laporan Poin 5", buffer.getvalue(), "Laporan_Audit_PBJ.xlsx")

else:
    st.info("Silakan unggah data untuk memproses.")
