import streamlit as st
import pandas as pd
import io

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Dashboard Rekonsiliasi", layout="wide", page_icon="📊")
st.markdown("""
<style>
body { background-color: #f4f6f7; }
.stat-card { background-color: #ffffff; padding: 15px; border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; }
.stat-label { font-size: 14px; color: #555; font-weight: bold; }
.stat-value { font-size: 22px; color: #0c2461; font-weight: bold; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# --- LOGO DI TENGAH ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.image("LOGO PEMPROV BARU.png", width=200)
    st.markdown("</div>", unsafe_allow_html=True)

# --- JUDUL ---
st.markdown("<h2 style='text-align: center;'>📌 Rekonsiliasi SIRUP & Realisasi</h2>", unsafe_allow_html=True)

# --- CONTINUE DENGAN LOGIKA CSV DAN RINGKASAN ---
# misal upload CSV, filter, hitung jumlah paket & anggaran, dsb.
# --- Contoh ringkasan ---
st.markdown("## 📊 Ringkasan Rekonsiliasi")
cols = st.columns([1.5,2,1.5,1.5,1.5,1.5])
cols[0].markdown(f"<div class='stat-card'><div class='stat-label'>✅ Sesuai RUP</div><div class='stat-value'>100 Paket</div><div>Rp 50.000.000</div></div>", unsafe_allow_html=True)
cols[1].markdown(f"<div class='stat-card'><div class='stat-label'>⚠️ Hanya Realisasi</div><div class='stat-value'>20 Paket</div><div>Rp 10.000.000</div></div>", unsafe_allow_html=True)
cols[2].markdown(f"<div class='stat-card'><div class='stat-label'>⏳ Belum Terealisasi</div><div class='stat-value'>15 Paket</div><div>Rp 8.000.000</div></div>", unsafe_allow_html=True)
cols[3].markdown(f"<div class='stat-card'><div class='stat-label'>🟢 Swakelola Tercatat</div><div class='stat-value'>5 Paket</div><div>Rp 3.500.000</div></div>", unsafe_allow_html=True)
cols[4].markdown(f"<div class='stat-card'><div class='stat-label'>🔴 Swakelola Tidak Tercatat</div><div class='stat-value'>2 Paket</div><div>Rp 1.200.000</div></div>", unsafe_allow_html=True)
cols[5].markdown(f"<div class='stat-card'><div class='stat-label'>🛒 Toko Daring</div><div class='stat-value'>10 Paket</div><div>Rp 5.000.000</div></div>", unsafe_allow_html=True)
