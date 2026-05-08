# --- 5. TABEL LAPORAN (PERBAIKAN TYPO VARIABEL) ---
    st.divider()
    st.subheader("📑 Laporan Audit Rekonsiliasi Per Satker")
    
    rekap_list = []
    satker_list = sorted(df_ren[satker_col].dropna().unique())
    
    for i, s in enumerate(satker_list, 1):
        ren_s = df_ren[df_ren[satker_col] == s]
        real_s = df_real_agg[df_real_agg[satker_col] == s]
        
        # Merge per Satker
        merge_s = pd.merge(ren_s[[rup_col, val_col]], real_s[[rup_col, val_col, 'Kat_Audit']], on=rup_col, how='right', indicator=True)
        
        sesuai_rup_df = merge_s[merge_s['_merge'] == 'both']
        tidak_sesuai_df = merge_s[merge_s['_merge'] == 'right_only']
        
        # Filter berdasarkan Kat_Audit (Sumber Transaksi)
        tokodaring_s = real_s[real_s['Kat_Audit'] == 'Tokodaring']
        swakelola_real_s = real_s[real_s['Kat_Audit'] == 'Swakelola'] # Nama variabel harus sama

        rekap_list.append({
            'No': i, 
            'Nama Satuan Kerja': s,
            'Sesuai RUP (Pkt)': len(sesuai_rup_df),
            'Sesuai RUP (Angg)': sesuai_rup_df[val_col + '_y'].sum(),
            'Swakelola Realisasi (Pkt)': len(swakelola_real_s), # SUDAH SAMA SEKARANG
            'Swakelola Realisasi (Angg)': swakelola_real_s[val_col].sum(),
            'Tokodaring (Pkt)': len(tokodaring_s),
            'Tokodaring (Angg)': tokodaring_s[val_col].sum(),
            'Tidak Sesuai RUP (Pkt)': len(tidak_sesuai_df),
            'Tidak Sesuai RUP (Angg)': tidak_sesuai_df[val_col + '_y'].sum(),
            'Selisih Anggaran': ren_s[val_col].sum() - real_s[val_col].sum(),
            'Identifikasi': "Overbudget" if (sesuai_rup_df[val_col + '_y'] > sesuai_rup_df[val_col + '_x']).any() else "Normal"
        })
