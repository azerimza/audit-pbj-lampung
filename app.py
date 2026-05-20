# --- Ringkasan Hasil Analisa (paket dihitung semua baris) ---
st.markdown("## 📌 Ringkasan Hasil Analisa")

# Perencanaan
df_ren_penyedia = df_ren[~df_ren['Metode Pengadaan'].str.contains('swakelola', na=False)]
df_ren_swakelola = df_ren[df_ren['Cara Pengadaan'].str.contains('swakelola', na=False)]

jml_paket_ren_penyedia = len(df_ren_penyedia)
anggaran_ren_penyedia = df_ren_penyedia[val_col].sum()
jml_paket_ren_swakelola = len(df_ren_swakelola)
anggaran_ren_swakelola = df_ren_swakelola[val_col].sum()

# Realisasi (paket dihitung semua baris)
df_real_penyedia = df_real[~df_real['Metode Pengadaan'].str.contains('swakelola', na=False)]
df_real_swakelola = df_real[df_real['Sumber Transaksi'].str.contains('swakelola', na=False)]

jml_paket_real_penyedia = len(df_real_penyedia)
anggaran_real_penyedia = df_real_penyedia[val_col].sum()
jml_paket_real_swakelola = len(df_real_swakelola)
anggaran_real_swakelola = df_real_swakelola[val_col].sum()

# Tampilkan ringkasan
st.markdown("### Perencanaan")
st.write(f"**Penyedia:** {jml_paket_ren_penyedia} Paket / Rp {anggaran_ren_penyedia:,.0f}")
st.write(f"**Swakelola:** {jml_paket_ren_swakelola} Paket / Rp {anggaran_ren_swakelola:,.0f}")

st.markdown("### Realisasi")
st.write(f"**Penyedia:** {jml_paket_real_penyedia} Paket / Rp {anggaran_real_penyedia:,.0f}")
st.write(f"**Swakelola:** {jml_paket_real_swakelola} Paket / Rp {anggaran_real_swakelola:,.0f}")
