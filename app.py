# --- 3. LOGIKA PEMROSESAN DATA ---
if file_ren and file_real:
    df_ren, df_real = read_csv_smart(file_ren), read_csv_smart(file_real)
    val_col, rup_col, satker_col = 'Total Nilai (Rp)', 'Kode RUP', 'Nama Satuan Kerja'
    
    # 1. Bersihkan Nama Kolom dari spasi
    df_ren.columns = df_ren.columns.str.strip()
    df_real.columns = df_real.columns.str.strip()

    # 2. KONVERSI KODE RUP MENJADI STRING (Mencegah ValueError)
    # Kita paksa keduanya jadi teks agar bisa digabungkan meskipun ada perbedaan format
    df_ren[rup_col] = df_ren[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)
    df_real[rup_col] = df_real[rup_col].astype(str).str.strip().str.replace('.0', '', regex=False)

    # 3. Konversi Angka Anggaran
    for df in [df_ren, df_real]:
        if val_col in df.columns:
            df[val_col] = pd.to_numeric(df[val_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0)

    # ... (lanjutkan ke kode kategori dan agregasi seperti sebelumnya)
