# --- RINGKASAN HASIL ANALISA DATA.INAPROC ---
df_ren_penyedia_analisa = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)]
df_ren_swakelola_analisa = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]
df_real_penyedia_analisa = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)]
df_real_swakelola_analisa = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]

def hitung_analisa(df, val=val_col):
    return len(df), df[val].sum() if val in df.columns else 0

jml_ren_penyedia, ang_ren_penyedia = hitung_analisa(df_ren_penyedia_analisa)
jml_ren_swakelola, ang_ren_swakelola = hitung_analisa(df_ren_swakelola_analisa)
jml_real_penyedia, ang_real_penyedia = hitung_analisa(df_real_penyedia_analisa)
jml_real_swakelola, ang_real_swakelola = hitung_analisa(df_real_swakelola_analisa)

st.markdown("## 📌 Ringkasan Hasil Analisa (Data.inaproc)")
cols = st.columns(4)
cols[0].markdown(f"<div class='stat-card'><div class='stat-label'>Perencanaan Penyedia</div><div class='stat-value'>{jml_ren_penyedia} Paket</div><div>Rp {ang_ren_penyedia:,.0f}</div></div>", unsafe_allow_html=True)
cols[1].markdown(f"<div class='stat-card'><div class='stat-label'>Perencanaan Swakelola</div><div class='stat-value'>{jml_ren_swakelola} Paket</div><div>Rp {ang_ren_swakelola:,.0f}</div></div>", unsafe_allow_html=True)
cols[2].markdown(f"<div class='stat-card'><div class='stat-label'>Realisasi Penyedia</div><div class='stat-value'>{jml_real_penyedia} Paket</div><div>Rp {ang_real_penyedia:,.0f}</div></div>", unsafe_allow_html=True)
cols[3].markdown(f"<div class='stat-card'><div class='stat-label'>Realisasi Swakelola</div><div class='stat-value'>{jml_real_swakelola} Paket</div><div>Rp {ang_real_swakelola:,.0f}</div></div>", unsafe_allow_html=True)

# --- DOWNLOAD EXCEL HASIL ANALISA ---
st.markdown("## 🗂️ Unduh Hasil Analisa")
download_analisa = {
    "Analisa_Perencanaan_Penyedia": df_ren_penyedia_analisa,
    "Analisa_Perencanaan_Swakelola": df_ren_swakelola_analisa,
    "Analisa_Realisasi_Penyedia": df_real_penyedia_analisa,
    "Analisa_Realisasi_Swakelola": df_real_swakelola_analisa
}
for name, df_dl in download_analisa.items():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        sheet_name = name[:31]  # pangkas sheet name <=31 char
        df_dl.to_excel(writer, sheet_name=sheet_name, index=False)
    st.download_button(f"📥 Download {name}", data=buf.getvalue(),
                       file_name=f"{name}_{satker_terpilih.replace(' ','_')}.xlsx",
                       use_container_width=True)
