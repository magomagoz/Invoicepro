import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import io

def create_excel_buffer(self, df, sheet_name):
    """Crea buffer Excel professionale con formattazione"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Ottieni workbook e worksheet per formattazione
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        # Auto-adjust colonne
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Intestazioni bold
        from openpyxl.styles import Font
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
    
    buffer.seek(0)
    return buffer.getvalue()

# Configurazione pagina
st.set_page_config(
    page_title="Fatturazione Attiva/Passiva",
    page_icon="💼",
    layout="wide"
)

# Carica/Salva dati
@st.cache_data
def carica_dati():
    if os.path.exists("fatture.json"):
        with open("fatture.json", "r") as f:
            return json.load(f)
    return {"Attiva": [], "Passiva": []}

def salva_dati(dati):
    with open("fatture.json", "w") as f:
        json.dump(dati, f, indent=4)

# Calcola totali
def calcola_totali(imponibile, iva_perc):
    try:
        imp = float(imponibile or 0)
        iva_p = float(iva_perc or 0) / 100
        iva = imp * iva_p
        totale = imp + iva
        return iva, totale
    except:
        return 0, 0

# Inizializza stato sessione
if 'dati_fatture' not in st.session_state:
    st.session_state.dati_fatture = carica_dati()
if 'pagina' not in st.session_state:
    st.session_state.pagina = "home"

# Sidebar navigazione
st.sidebar.title("CONFIGURAZIONE")
if st.sidebar.button("🏠 **FATTURAZIONE**", use_container_width=True):
    st.session_state.pagina = "home"

if st.sidebar.button("📋 **ARCHIVIO FATTURE**", use_container_width=True):
    st.session_state.pagina = "storico"

# PAGINA HOME - Scelta tipo fatturazione CON LOGO
if st.session_state.pagina == "home":
    # Header con logo a DESTRA
    #st.markdown('<div class="main-header"><div class="title-container">', unsafe_allow_html=True)
    #st.markdown('<h1 style="color: #4CAF50; margin: 0;">💼 Gestione Fatturazione</h1>', unsafe_allow_html=True)
    #st.markdown('</div><div class="logo-container">', unsafe_allow_html=True)
    
    # LOGO - sostituisci "logo.png" con il nome del tuo file
    st.image("logo.png", use_column_width=False)
    
    st.markdown('</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")

    # Layout principale con sidebar
    st.title("💼 Fatturazione aziendale")
    st.markdown("---")

    
    st.markdown("*Scegli il tipo di fatturazione*")
    
    col1, col2 = st.columns(2, gap="small")
    
    with col1:
        if st.button("📤 **FATTURAZIONE ATTIVA**  \n_Fatture emesse ai clienti_", 
                    type="primary", use_container_width=True, help="Crea fattura per i tuoi clienti"):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Attiva"
            st.rerun()
    
    with col2:
        if st.button("📥 **FATTURAZIONE PASSIVA**  \n_Fatture ricevute dai fornitori_", 
                    type="secondary", use_container_width=True, help="Registra fatture fornitori"):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Passiva"
            st.rerun()

# FORM FATTURAZIONE
elif st.session_state.pagina == "form":
    tipo = st.session_state.tipo
    st.header(f"📄 {tipo} - Nuova Fattura")
    
    # Form in due colonne
    col1, col2 = st.columns(2)
    
    with col1:
        data = st.date_input("Data", value=datetime.now())
        numero = st.text_input("Numero Protocollo", value=f"2026/{len(st.session_state.dati_fatture[tipo])+1}")
        nome = st.text_input("Cliente/Fornitore", 
                           value="Cliente" if tipo == "Attiva" else "Fornitore")
        piva = st.text_input("P.IVA / CF", value="")
    
    with col2:
        imponibile = st.number_input("Imponibile (€)", min_value=0.0, step=0.01, format="%.2f")
        iva_perc = st.number_input("Aliquota IVA (%)", min_value=0.0, value=22.0, step=0.1)
        pagamento = st.selectbox("Modalità Pagamento", 
                               ["Bonifico 30gg", "Bonifico 60gg", "Anticipo", "Contanti"])
    
    # Calcolo totali live
    iva, totale = calcola_totali(imponibile, iva_perc)
    col_tot1, col_tot2, _ = st.columns(3)
    col_tot1.metric("IVA", f"€ {iva:.2f}")
    col_tot2.metric("TOTALE", f"€ {totale:.2f}")
    
    # Note
    note = st.text_area("Note", height=100)
    
    # Pulsanti azione
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("💾 Salva Fattura", type="primary", use_container_width=True):
            fattura = {
                "data": data.strftime("%d/%m/%Y"),
                "numero": numero,
                "cliente_fornitore": nome,
                "piva": piva,
                "imponibile": float(imponibile),
                "iva_perc": float(iva_perc),
                "iva": float(iva),
                "totale": float(totale),
                "pagamento": pagamento,
                "note": note,
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.dati_fatture[tipo].append(fattura)
            salva_dati(st.session_state.dati_fatture)
            st.success("✅ Fattura salvata!")
            st.balloons()
            st.rerun()
    
    with col_btn2:
        if st.button("⬅️ Indietro", use_container_width=True):
            st.session_state.pagina = "home"
            st.rerun()
    
    with col_btn3:
        if st.button("🖨️ Stampa PDF", use_container_width=True):
            st.info("📄 PDF pronto! (Implementa reportlab per export reale)")

# STORICO FATTURE (SEZIONE AGGIORNATA)
elif st.session_state.pagina == "storico":
    st.header("📋 Storico Fatture")
    
    # Statistiche
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fatture Attive", len(st.session_state.dati_fatture["Attiva"]))
    col2.metric("Fatture Passive", len(st.session_state.dati_fatture["Passiva"]))
    totale_attive = sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Attiva'])
    totale_passive = sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Passiva'])
    col3.metric("Totale Attive", f"€ {totale_attive:.2f}")
    col4.metric("Totale Passive", f"€ {totale_passive:.2f}")
    
    # Bottoni export principali
    col_exp1, col_exp2, _ = st.columns(2)
    with col_exp1:
        if st.button("📊 **Esporta TUTTE Attive in Excel**", type="primary", use_container_width=True):
            df = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            buffer = self.create_excel_buffer(df, "Fatture_Attive")
            st.download_button(
                label="💾 Scarica Excel Attive",
                data=buffer,
                file_name=f"Fatture_Attive_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    with col_exp2:
        if st.button("📊 **Esporta TUTTE Passive in Excel**", type="secondary", use_container_width=True):
            df = pd.DataFrame(st.session_state.dati_fatture["Passiva"])
            buffer = self.create_excel_buffer(df, "Fatture_Passive")
            st.download_button(
                label="💾 Scarica Excel Passive",
                data=buffer,
                file_name=f"Fatture_Passive_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # Tabs per tipo CON EXPORT DEDICATO
    tab1, tab2 = st.tabs(["📤 Fatturazione Attiva", "📥 Fatturazione Passiva"])
    
    with tab1:
        if st.session_state.dati_fatture["Attiva"]:
            df_attive = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            
            # Bottoni export specifici per tab
            col1, col2 = st.columns(2)
            with col1:
                if st.download_button(
                    label="⬇️ **Excel Attive**",
                    data=self.create_excel_buffer(df_attive, "Fatture_Attive"),
                    file_name=f"Attive_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                ):
                    st.success("✅ Excel scaricato!")
            
            with col2:
                csv = df_attive.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 CSV Attive",
                    data=csv,
                    file_name=f"Attive_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv',
                    use_container_width=True
                )
            
            st.dataframe(df_attive, use_container_width=True, hide_index=True)
        else:
            st.info("👆 Nessuna fattura attiva. Crea la prima dalla Home!")
    
    with tab2:
        if st.session_state.dati_fatture["Passiva"]:
            df_passive = pd.DataFrame(st.session_state.dati_fatture["Passiva"])
            
            # Bottoni export specifici per tab
            col1, col2 = st.columns(2)
            with col1:
                if st.download_button(
                    label="⬇️ **Excel Passive**",
                    data=self.create_excel_buffer(df_passive, "Fatture_Passive"),
                    file_name=f"Passive_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                ):
                    st.success("✅ Excel scaricato!")
            
            with col2:
                csv = df_passive.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 CSV Passive",
                    data=csv,
                    file_name=f"Passive_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv',
                    use_container_width=True
                )
            
            st.dataframe(df_passive, use_container_width=True, hide_index=True)
        else:
            st.info("👆 Nessuna fattura passiva. Crea la prima dalla Home!")
