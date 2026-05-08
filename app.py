import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.express as px

# --- 1. CONFIG ---
st.set_page_config(page_title="E-Audit PBJ Lampung", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #0c2461; color: white; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #0c2461; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1, h2 { color: #0c2461; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def clean_rup(val):
    if pd.isna(val) or val == "": return ""
    return ''.join(filter(str.isdigit, str(val)))

def read_csv_smart(file):
    try:
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
    except:
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='cp1252')

# --- 2. SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Lampung_Coats_of_arms.svg/1200px-Lampung_Coats_of_arms.svg.png", width=60)
    st.markdown("### **SISTEM AUDIT DIGITAL**")
    st.markdown("**Analis:** Reza Saputra Azmi\n\n**Biro PBJ Lampung**")
    st.divider()
    file_ren = st.file_uploader("1. Upload Data SIRUP (CSV)", type=['csv'])
    file_real = st.file_uploader("2. Upload Data Realisasi (CSV)", type=['csv'])
    st.caption("v5.2 | Budget Tracking Enabled")

# --- 3. ENGINE ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    rup_col, val_col = 'Kode RUP', 'Total Nilai (Rp)'

    if rup_col in df_ren.columns and rup_col in df_real.columns:
        df_ren['ID_RUP_CLEAN'] = df_ren[rup_col].astype(str).apply(clean_rup)
        df_real['ID_RUP_CLEAN'] = df_real[rup_col].astype(str).apply(clean_rup)
        
        for d in [df_ren, df_real]:
            if val_col in d.columns:
                d[val_col] = pd.to_numeric(d[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

        # Perhitungan Rekap per OPD
        satkers = sorted(list(set(df_ren['Nama Satuan Kerja'].dropna().unique()) | set(df_real['Nama Satuan Kerja'].dropna().unique())))
        list_rekap = []
        for s in satkers:
            ren_s = df_ren[df_ren['Nama Satuan Kerja'] == s]
            real_s = df_real[df_real['Nama Satuan Kerja'] == s]
            
            ang_ren = ren_s[val_col].sum()
            ang_real = real_s[val_col].sum()
            sisa = ang_ren - ang_real
            
            list_rekap.append({
                'Nama Satuan Kerja': s,
                'Paket Rencana': len(ren_s),
                'Paket Realisasi': real_s['ID_RUP_CLEAN'].nunique(),
                'Anggaran Rencana': ang_ren,
                'Anggaran Realisasi': ang_real,
                'Sisa Anggaran': sisa,
                'Persentase Penyerapan': (ang_real / ang_ren * 100) if ang_ren > 0 else 0
            })
        df_rekap = pd.DataFrame(list_rekap)

        st.markdown("# ⚖️ ANALISIS ANGGARAN & PENYERAPAN")
        
        # --- TOP METRICS ---
        m1, m2, m3 = st.columns(3)
        total_ren = df_rekap['Anggaran Rencana'].sum()
        total_real = df_rekap['Anggaran Realisasi'].sum()
        total_sisa = total_ren - total_real
        
        m1.metric("Total Pagu Rencana", f"Rp {total_ren/1e9:.2f} M")
        m2.metric("Total Realisasi", f"Rp {total_real/1e9:.2f} M")
        m3.metric("Total Sisa Anggaran", f"Rp {total_sisa/1e9:.2f} M", delta=f"{(total_real/total_ren*100):.1f}% Serap", delta_color="normal")

        st.divider()

        # --- TABS ---
        t1, t2 = st.tabs(["📊 Statistik Sisa Anggaran", "📝 Tabel Detail OPD"])

        with t1:
            st.subheader("Visualisasi Sisa Anggaran per OPD")
            # Grafik Sisa Anggaran
            fig_sisa = px.bar(df_rekap, x='Nama Satuan Kerja', y='Sisa Anggaran', 
                              color='Sisa Anggaran', 
                              color_continuous_scale='RdYlGn', # Merah jika sedikit/minus, Hijau jika banyak sisa
                              title='Distribusi Sisa Anggaran (Efisiensi)')
            st.plotly_chart(fig_sisa, use_container_width=True)
            
            # Grafik Penyerapan
            fig_pie = px.sunburst(df_rekap, path=['Nama Satuan Kerja'], values='Anggaran Realisasi',
                                  title='Proporsi Realisasi Anggaran antar OPD')
            st.plotly_chart(fig_pie, use_container_width=True)

        with t2:
            st.subheader("Data Lengkap Penyerapan")
            
            # Formatting untuk tabel
            def format_rupiah(val):
                return f"Rp {val:,.0f}"
            
            def highlight_sisa(s):
                return 'color: red; font-weight: bold' if s < 0 else 'color: green'

            st.dataframe(
                df_rekap.style.format({
                    'Anggaran Rencana': format_rupiah,
                    'Anggaran Realisasi': format_rupiah,
                    'Sisa Anggaran': format_rupiah,
                    'Persentase Penyerapan': '{:.2f}%'
                }).applymap(highlight_sisa, subset=['Sisa Anggaran']),
                use_container_width=True
            )
            
            # Download
            out = io.BytesIO()
            df_rekap.to_excel(out, index=False)
            st.download_button("📥 Ekspor Laporan Sisa Anggaran (.xlsx)", out.getvalue(), "Rekap_Sisa_Anggaran_PBJ.xlsx")

        # --- ALERTS ---
        if any(df_rekap['Sisa Anggaran'] < 0):
            st.error("### 🚨 PERINGATAN DEFISIT")
            defisit_opd = df_rekap[df_rekap['Sisa Anggaran'] < 0]
            for _, r in defisit_opd.iterrows():
                st.warning(f"**{r['Nama Satuan Kerja']}** melampaui pagu sebesar **Rp {abs(r['Sisa Anggaran']):,.0f}**")

    else:
        st.error("Header kolom 'Kode RUP' atau 'Total Nilai (Rp)' tidak sesuai.")
else:
    st.info("Upload file CSV untuk melihat sisa anggaran.")
