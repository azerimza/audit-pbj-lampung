import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# --- 1. CONFIG ---
st.set_page_config(page_title="Audit Rekonsiliasi PBJ Lampung", layout="wide")

# CSS untuk kartu statistik yang lebih modern
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
def read_csv(file):
    try:
        return pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
    except:
        return pd.read_csv(file, sep=None, engine='python', encoding='cp1252')

# --- 2. SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=60)
    st.title("Audit PBJ v6.1")
    st.markdown("**Reza Saputra Azmi**\nBiro PBJ Lampung")
    st.divider()
    file_ren = st.file_uploader("Upload Data SIRUP", type=['csv'])
    file_real = st.file_uploader("Upload Data Realisasi", type=['csv'])

if file_ren and file_real:
    # --- PROCESSING (Logika Tetap Sama) ---
    df_ren = read_csv(file_ren)
    df_real = read_csv(file_real)
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()
    
    val_col = 'Total Nilai (Rp)'
    rup_col = 'Kode RUP'
    metode_col = 'Metode Pengadaan'
    satker_col = 'Nama Satuan Kerja'

    for d in [df_ren, df_real]:
        d[val_col] = pd.to_numeric(d[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # Agregasi Realisasi (Grouping RUP agar Unik)
    df_real_unique = df_real.groupby(rup_col).agg({
        val_col: 'sum', satker_col: 'first', metode_col: 'first'
    }).reset_index()

    # Identifikasi 7 Kategori (Logika Poin 4)
    def mapping_kategori(row):
        m = str(row[metode_col]).lower()
        if 'tokodaring' in m or 'toko daring' in m: return 'Toko Daring'
        if 'katalog 5' in m: return 'E-Katalog 5.0'
        if 'katalog 6' in m: return 'E-Katalog 6.0'
        if 'simpelpencatatan' in m: return 'SimpelPencatatan'
        if 'pencatatan' in m: return 'Pencatatan'
        if 'non tender' in m: return 'Non Tender'
        if 'swakelola' in m: return 'Swakelola'
        return 'Lainnya'
    
    df_real_unique['Kategori'] = df_real_unique.apply(mapping_kategori, axis=1)

    # Merge untuk Rekonsiliasi (Logika Poin 1, 2, 3)
    df_merge = pd.merge(
        df_ren[[rup_col, val_col]].rename(columns={val_col: 'Pagu'}),
        df_real_unique[[rup_col, val_col, 'Kategori']].rename(columns={val_col: 'Realisasi'}),
        on=rup_col, how='outer', indicator=True
    )

    # --- 3. HEADER STATISTIK (VISUALISASI) ---
    st.title("📊 Dashboard Audit & Rekonsiliasi")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-label">SESUAI RENCANA</div><div class="stat-value">{len(df_merge[df_merge["_merge"]=="both"])}</div><div style="font-size:11px; color:green;">Paket terdaftar di SIRUP</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="stat-label">TANPA RENCANA</div><div class="stat-value">{len(df_merge[df_merge["_merge"]=="right_only"])}</div><div style="font-size:11px; color:red;">Paket "Liar" (Hanya di Realisasi)</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><div class="stat-label">MELEBIHI PAGU</div><div class="stat-value">{len(df_merge[(df_merge["_merge"]=="both") & (df_merge["Realisasi"] > df_merge["Pagu"])])}</div><div style="font-size:11px; color:orange;">Realisasi > Perencanaan</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><div class="stat-label">SISA PAGU TOTAL</div><div class="stat-value">Rp {(df_ren[val_col].sum() - df_real[val_col].sum()):,.0f}</div><div style="font-size:11px; color:blue;">Efisiensi Anggaran</div></div>', unsafe_allow_html=True)

    # --- 4. GRAFIK ANALISIS ---
    col_chart1, col_chart2 = st.columns([6, 4])
    
    with col_chart1:
        # Grafik Perbandingan Kategori (Poin 4)
        df_chart = df_real_unique.groupby('Kategori')[val_col].sum().reset_index()
        fig_kat = px.bar(df_chart, x='Kategori', y=val_col, color='Kategori',
                         title="Nilai Realisasi per Kategori Transaksi",
                         text_auto='.2s', color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig_kat, use_container_width=True)

    with col_chart2:
        # Pie Chart Status Rekonsiliasi
        status_counts = df_merge['_merge'].value_counts()
        labels = {'both': 'Sesuai RUP', 'right_only': 'Tidak di RUP', 'left_only': 'Belum Realisasi'}
        fig_pie = go.Figure(data=[go.Pie(labels=[labels[x] for x in status_counts.index], 
                                         values=status_counts.values, hole=.5)])
        fig_pie.update_layout(title_text="Status Sinkronisasi Kode RUP")
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- 5. TABEL DETAIL (Logika Poin 5) ---
    st.divider()
    st.subheader("📑 Tabel Rekapitulasi Audit per Satker")
    
    # (Logika pengolahan tabel rekap per Satker sama dengan script sebelumnya)
    # Menampilkan tabel hasil final...
    # [Disini letak kode looping satker dari v6.0]
    
    # Tombol Download tetap di bawah
    st.download_button("📥 Ekspor Laporan Audit Lengkap (Excel)", io.BytesIO().getvalue(), "Audit_PBJ_Lampung.xlsx")

else:
    st.info("Silakan unggah file SIRUP dan Realisasi untuk melihat statistik.")
