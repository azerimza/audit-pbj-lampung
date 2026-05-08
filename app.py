import streamlit as st
import pandas as pd
import numpy as np
from thefuzz import fuzz, process
import io

# 1. KONFIGURASI HALAMAN & TEMA
st.set_page_config(
    page_title="Sistem Rekonsiliasi PBJ Lampung",
    page_icon="⚖️",
    layout="wide"
)

# Custom CSS untuk tampilan lebih tajam
st.markdown("""
    <style>
    .main {
        background-color: #f4f7f9;
    }
    [data-testid="stSidebar"] {
        background-color: #0c2461;
        color: white;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    h1, h2, h3 {
        color: #0c2461;
        font-weight: 700;
    }
    .stButton>button {
        background-color: #0c2461;
        color: white;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNGSI LOGIKA
def clean_rup(val):
    if pd.isna(val): return ""
    return ''.join(filter(str.isdigit, str(val)))

# 3. SIDEBAR (DENGAN TULISAN BARU)
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=80)
    st.title("ADMINISTRATOR SISTEM")
    st.write(f"**Analis:**\nReza Saputra Azmi, S.T.")
    st.write("**Satker:**\nBiro PBJ Prov. Lampung")
    st.divider()
    
    st.subheader("PENGINPUTAN DATA")
    file_ren = st.file_uploader("Data Perencanaan (SIRUP)", type=['xlsx'])
    file_real = st.file_uploader("Data Realisasi (E-Katalog)", type=['xlsx'])
    st.divider()
    st.caption("E-Audit v2.1 | Biro PBJ Lampung")

# 4. PROSES DATA & TAMPILAN UTAMA
if file_ren and file_real:
    df_ren = pd.read_excel(file_ren, dtype=str)
    df_real = pd.read_excel(file_real, dtype=str)
    
    # Cleaning
    df_ren['ID_RUP_CLEAN'] = df_ren.iloc[:, 0].apply(clean_rup)
    df_real['ID_RUP_CLEAN'] = df_real.iloc[:, 0].apply(clean_rup)
    
    # Audit Join
    df_join = pd.merge(df_real, df_ren, on='ID_RUP_CLEAN', how='left', suffixes=('_REAL', '_REN'))
    
    # Logika Status
    df_join['Status'] = df_join.apply(lambda x: "✅ VALID" if pd.notna(x.get('ID_RUP_CLEAN')) and x['ID_RUP_CLEAN'] != "" else "⚠️ TIDAK DITEMUKAN", axis=1)

    # HEADER DASHBOARD
    st.title("⚖️ REKONSILIASI DATA PBJ")
    st.info(f"Sistem Otomasi Validasi Kesesuaian Rencana dan Realisasi Pengadaan Barang/Jasa Provinsi Lampung.")

    # TABEL METRIK
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Paket Realisasi", f"{len(df_join)} Paket")
    with m2:
        match_count = len(df_join[df_join['Status'] == "✅ VALID"])
        st.metric("Tingkat Validasi", f"{match_count} Paket", f"{(match_count/len(df_join)*100):.1f}%")
    with m3:
        st.metric("Anomali (ID RUP)", f"{len(df_join) - match_count} Temuan", delta_color="inverse")

    st.divider()

    # TABS DETAIL
    tab_audit, tab_grafik = st.tabs(["📝 Laporan Hasil Validasi", "📊 Analisis Visual"])

    with tab_audit:
        st.subheader("Data Hasil Rekonsiliasi")
        
        # Pewarnaan baris otomatis
        def highlight_status(val):
            color = '#ffdada' if val == "⚠️ TIDAK DITEMUKAN" else '#e1f5e6'
            return f'background-color: {color}'
        
        st.dataframe(df_join.style.applymap(highlight_status, subset=['Status']), use_container_width=True)
        
        # Export Button
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_join.to_excel(writer, index=False)
        st.download_button("📥 Unduh Laporan Rekonsiliasi (.xlsx)", output.getvalue(), "Laporan_Rekonsiliasi_PBJ.xlsx")

    with tab_grafik:
        col_left, col_right = st.columns(2)
        with col_left:
            st.write("**Status Validasi ID RUP**")
            st.bar_chart(df_join['Status'].value_counts())
        with col_right:
            st.write("**Tabel Ringkasan Status**")
            st.table(df_join['Status'].value_counts())

else:
    # Tampilan awal
    st.title("⚖️ Sistem Rekonsiliasi Data PBJ")
    st.subheader("Biro Pengadaan Barang dan Jasa Provinsi Lampung")
    st.markdown("""
    Selamat datang, **Mas Reza**. Silakan lakukan pembaruan data dengan mengunggah 
    dokumen perencanaan dan realisasi pada bilah navigasi di sebelah kiri.
    
    ---
    **Fungsi Utama:**
    * **Automated Matching:** Pencocokan ID RUP antar platform secara instan.
    * **Anomaly Detection:** Mengidentifikasi belanja yang tidak tercatat dalam SIRUP.
    * **Data Export:** Menghasilkan laporan audit format Excel yang siap dilaporkan.
    """)
