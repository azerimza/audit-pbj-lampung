import streamlit as st
import pandas as pd
import io

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Dashboard Rekonsiliasi", layout="wide", page_icon="📊")

st.markdown("""
<style>
body { background-color: #f4f6f7; }
.stat-card {
    background-color: #ffffff; 
    padding: 15px; 
    border-radius: 10px; 
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
    text-align: center; 
    margin-bottom: 20px;
}
.stat-label { font-size: 14px; color: #555; font-weight: bold; }
.stat-value { font-size: 22px; color: #0c2461; font-weight: bold; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# --- LOGO DI TENGAH ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    logo_file = st.file_uploader("Upload Logo (opsional)", type=['png','jpg'])
    if logo_file:
        st.image(logo_file, width=120)
    st.markdown("<h2 style='text-align: center;'>📌 Rekonsiliasi SIRUP & Realisasi</h2>", unsafe_allow_html=True)

# --- SIDEBAR UNTUK UPLOAD CSV ---
with st.sidebar:
    st.markdown("## Upload Data CSV")
    file_ren = st.file_uploader("1. Upload Data Perencanaan (RUP)", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi", type=['csv'])
    st.divider()

# --- LOGIKA UTAMA ---
if file_ren and file_real:
    df_ren = pd.read_csv(file_ren)
    df_real = pd.read_csv(file_real)
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'

    # Bersihkan nama kolom
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()
    for df in [df_ren, df_real]:
        if rup_col in df.columns:
            df[rup_col] = df[rup_col].astype(str).str.strip()
        if 'Metode Pengadaan' in df.columns:
            df['Metode Pengadaan'] = df['Metode Pengadaan'].astype(str).str.lower()
        if 'Sumber Transaksi' in df.columns:
            df['Sumber Transaksi'] = df['Sumber Transaksi'].astype(str).str.lower()

    # --- 1️⃣ Sesuai RUP (Penyedia) ---
    df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_ren.columns else df_ren.copy()
    df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_real.columns else df_real.copy()
    if val_col in df_real_penyedia.columns:
        df_real_penyedia_sum = df_real_penyedia.groupby(rup_col, as_index=False)[val_col].sum()
    else:
        df_real_penyedia_sum = pd.DataFrame(columns=[rup_col,val_col])
    df_sesuai = pd.merge(df_ren_penyedia.drop_duplicates(subset=[rup_col]), df_real_penyedia_sum, on=rup_col, how='inner') if not df_ren_penyedia.empty and not df_real_penyedia_sum.empty else pd.DataFrame(columns=[rup_col,val_col])
    jumlah_paket_sesuai = len(df_sesuai)
    jumlah_anggaran_sesuai = df_sesuai[val_col].sum() if val_col in df_sesuai.columns else 0

    # --- 2️⃣ Hanya Realisasi (penyedia biasa) ---
    if 'Metode Pengadaan' in df_real.columns and 'Sumber Transaksi' in df_real.columns:
        df_real_only = df_real[(~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)) &
                                (~df_real['Sumber Transaksi'].str.contains('tokodaring', na=False))]
        if rup_col in df_ren.columns:
            df_real_only = df_real_only[~df_real_only[rup_col].isin(df_ren[rup_col])]
        jumlah_paket_real_only = len(df_real_only)
        jumlah_anggaran_real_only = df_real_only[val_col].sum() if val_col in df_real_only.columns else 0
    else:
        df_real_only = pd.DataFrame(columns=df_real.columns)
        jumlah_paket_real_only = 0
        jumlah_anggaran_real_only = 0

    # --- 3️⃣ Swakelola ---
    df_ren_swa = df_ren[df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_ren.columns else pd.DataFrame()
    df_real_swa = df_real[df_real['Metode Pengadaan'].str.contains('swakelola', na=False)] if 'Metode Pengadaan' in df_real.columns else pd.DataFrame()
    if not df_ren_swa.empty and not df_real_swa.empty and val_col in df_real_swa.columns:
        df_swakelola = pd.merge(df_ren_swa.drop_duplicates(subset=[rup_col]), df_real_swa.groupby(rup_col, as_index=False)[val_col].sum(), on=rup_col, how='inner')
    else:
        df_swakelola = pd.DataFrame(columns=[rup_col,val_col])
    jumlah_paket_swakelola = len(df_swakelola)
    jumlah_anggaran_swakelola = df_swakelola[val_col].sum() if val_col in df_swakelola.columns else 0

    # --- 4️⃣ Tokodaring ---
    if 'Sumber Transaksi' in df_real.columns:
        df_tokodaring = df_real[df_real['Sumber Transaksi'].str.contains('tokodaring', na=False)]
        jumlah_paket_tokodaring = len(df_tokodaring)
        jumlah_anggaran_tokodaring = df_tokodaring[val_col].sum() if val_col in df_tokodaring.columns else 0
    else:
        df_tokodaring = pd.DataFrame(columns=df_real.columns)
        jumlah_paket_tokodaring = 0
        jumlah_anggaran_tokodaring = 0

    # --- DASHBOARD METRIK ---
    st.markdown("## 📊 Ringkasan Rekonsiliasi")
    c1, c2, c3, c4 = st.columns([1.5,2,1.5,1.5])
    c1.markdown(f"<div class='stat-card'><div class='stat-label'>✅ Sesuai RUP</div><div class='stat-value'>{jumlah_paket_sesuai} Paket</div><div>Rp {jumlah_anggaran_sesuai:,.0f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-card' style='border-top: 5px solid #e67e22;'><div class='stat-label'>⚠️ Hanya Realisasi</div><div class='stat-value'>{jumlah_paket_real_only} Paket</div><div>Rp {jumlah_anggaran_real_only:,.0f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-card' style='border-top: 5px solid #27ae60;'><div class='stat-label'>🟢 Swakelola</div><div class='stat-value'>{jumlah_paket_swakelola} Paket</div><div>Rp {jumlah_anggaran_swakelola:,.0f}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='stat-card' style='border-top: 5px solid #9b59b6;'><div class='stat-label'>🛒 Tokodaring</div><div class='stat-value'>{jumlah_paket_tokodaring} Paket</div><div>Rp {jumlah_anggaran_tokodaring:,.0f}</div></div>", unsafe_allow_html=True)

    # --- TAB TABEL DETAIL ---
    st.markdown("## 📑 Tabel Detail per Kategori")
    tab1, tab2, tab3, tab4 = st.tabs(["Sesuai RUP", "Hanya Realisasi", "Swakelola", "Tokodaring"])
    with tab1: st.dataframe(df_sesuai, use_container_width=True)
    with tab2: st.dataframe(df_real_only, use_container_width=True)
    with tab3: st.dataframe(df_swakelola, use_container_width=True)
    with tab4: st.dataframe(df_tokodaring, use_container_width=True)

    # --- DOWNLOAD EXCEL PER KATEGORI ---
    st.markdown("## 🗂️ Unduh Laporan Excel")
    download_data = {"Sesuai_RUP": df_sesuai, "Hanya_Realisasi": df_real_only, "Swakelola": df_swakelola, "Tokodaring": df_tokodaring}
    for name, df_dl in download_data.items():
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df_dl.to_excel(writer, sheet_name=name, index=False)
        st.download_button(f"📥 Download {name}", data=buf.getvalue(), file_name=f"Laporan_{name}.xlsx", use_container_width=True)

else:
    st.info("👋 Silakan unggah file Perencanaan dan Realisasi di sidebar.")
