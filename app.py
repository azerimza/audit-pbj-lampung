import streamlit as st
import pandas as pd
import io

# ... (Kode styling dan pembersihan data sebelumnya tetap sama) ...

if st.session_state.data_proses is not None:
    # --- (Ambil data dari session state seperti sebelumnya) ---
    dp = st.session_state.data_proses
    # ... 
    
    # --- 1. TAMPILAN LAPORAN FORMAL (DI DASHBOARD) ---
    st.markdown("---")
    st.markdown("### 📋 Laporan Ringkasan Rekonsiliasi")
    
    # Hitung data untuk tabel laporan
    pagu_penyedia = df_ren_penyedia_analisa[val_col].sum()
    real_penyedia = df_sesuai['Anggaran_Realisasi'].sum()
    
    pagu_swa = df_ren_swakelola_analisa[val_col].sum()
    real_swa = df_swakelola_tercatat['Anggaran_Realisasi'].sum()

    # Buat DataFrame untuk tampilan laporan
    data_laporan = {
        "Uraian": ["Penyedia", "Swakelola", "TOTAL"],
        "Pagu Perencanaan (RUP)": [pagu_penyedia, pagu_swa, pagu_penyedia + pagu_swa],
        "Realisasi Tercatat": [real_penyedia, real_swa, real_penyedia + real_swa],
        "Selisih (Gap)": [pagu_penyedia - real_penyedia, pagu_swa - real_swa, (pagu_penyedia + pagu_swa) - (real_penyedia + real_swa)],
        "% Capaian": [
            (real_penyedia/pagu_penyedia*100) if pagu_penyedia > 0 else 0,
            (real_swa/pagu_swa*100) if pagu_swa > 0 else 0,
            ((real_penyedia+real_swa)/(pagu_penyedia+pagu_swa)*100) if (pagu_penyedia+pagu_swa) > 0 else 0
        ]
    }
    df_lap_tampilan = pd.DataFrame(data_laporan)
    
    # Tampilkan tabel dengan format mata uang
    st.table(df_lap_tampilan.style.format({
        "Pagu Perencanaan (RUP)": "Rp {:,.0f}",
        "Realisasi Tercatat": "Rp {:,.0f}",
        "Selisih (Gap)": "Rp {:,.0f}",
        "% Capaian": "{:.2f}%"
    }))

    # --- 2. FUNGSI EKSPOR EXCEL TERFORMAT (LAYOUT LAPORAN) ---
    def generate_formatted_excel(df_summary, dict_details, satker_name):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # FORMATTING
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#0c2461', 'color': 'white', 'border': 1, 'align': 'center'})
            title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
            currency_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1})
            percent_fmt = workbook.add_format({'num_format': '0.00%', 'border': 1})
            border_fmt = workbook.add_format({'border': 1})

            # --- SHEET 1: RINGKASAN LAPORAN ---
            sheet_name = 'Laporan_Ringkasan'
            df_summary.to_excel(writer, sheet_name=sheet_name, index=False, startrow=4)
            worksheet = writer.sheets[sheet_name]
            
            # Tulis Judul Laporan di Atas
            worksheet.write('A1', 'LAPORAN REKONSILIASI PERENCANAAN DAN REALISASI', title_fmt)
            worksheet.write('A2', f'SATUAN KERJA: {satker_name.upper()}')
            
            # Terapkan Format ke Header Tabel Ringkasan
            for col_num, value in enumerate(df_summary.columns.values):
                worksheet.write(4, col_num, value, header_fmt)
                worksheet.set_column(col_num, col_num, 25) # Perlebar kolom

            # Terapkan format angka
            row_count = len(df_summary)
            worksheet.set_column('B:D', 20, currency_fmt)
            worksheet.set_column('E:E', 15, percent_fmt)

            # --- SHEET LAINNYA: DETAIL DATA ---
            for name, df_detail in dict_details.items():
                df_detail.to_excel(writer, sheet_name=name[:31], index=False)
                ws_detail = writer.sheets[name[:31]]
                # Format header detail
                for col_num, value in enumerate(df_detail.columns.values):
                    ws_detail.write(0, col_num, value, header_fmt)
                ws_detail.set_column(0, len(df_detail.columns), 18)

        return output.getvalue()

    # Tombol Download Baru
    st.markdown("### 📥 Ekspor Laporan Lengkap")
    
    # Siapkan data detail untuk sheet excel
    dict_detail_data = {
        "Detail_Sesuai_RUP": df_sesuai,
        "Detail_Hanya_Realisasi": df_real_only,
        "Detail_Belum_Realisasi": df_belum_teralisasi,
        "Swakelola_Tercatat": df_swakelola_tercatat,
        "Toko_Daring": df_tokodaring
    }
    
    excel_data = generate_formatted_excel(df_lap_tampilan, dict_detail_data, satker_terpilih)
    
    st.download_button(
        label="Download Laporan Format Excel (Sesuai Layout)",
        data=excel_data,
        file_name=f"LAPORAN_REKONSILIASI_{satker_terpilih.replace(' ','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
