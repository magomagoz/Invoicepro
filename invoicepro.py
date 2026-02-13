import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import io

# ✅ CORRETTO  
def create_excel_buffer(df, sheet_name):  # ← RIMUOVI self
    """Crea buffer Excel professionale con formattazione"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        
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
    page_title="Invoice Pro",
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

# Sidebar COMPLETA con Anno + Anagrafiche
st.sidebar.title("📊 **CONFIGURAZIONE**")

# === SELETTORE ANNO (2020-2050) ===
anni = list(range(2020, 2051))
anno_selezionato = st.sidebar.selectbox(
    "📅 **Anno Fatture**", 
    anni, 
    index=anni.index(2026),  # Default 2026
    help="Filtra fatture per anno"
)
st.sidebar.markdown("---")

# Navigazione esistente
if st.sidebar.button("🏠 **FATTURAZIONE**", use_container_width=True):
    st.session_state.pagina = "home"

if st.sidebar.button("📋 **ARCHIVIO FATTURE**", use_container_width=True):
    st.session_state.pagina = "storico"

# === NUOVO PULSANTE ANAGRAFICHE ===
if st.sidebar.button("👥 **ANAGRAFICHE**", use_container_width=True):
    st.session_state.pagina = "anagrafiche"

# Info anno selezionato
st.sidebar.info(f"**Filtro attivo: {anno_selezionato}**")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("### 🟢 **FATTURE ATTIVE**")
        st.markdown("*Fatture emesse ai clienti*")
        if st.button("**INIZIA →**", key="attiva_go", use_container_width=True):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Attiva"
            st.rerun()
    
    with col2:
        st.markdown("### 🔵 **FATTURE PASSIVE**")
        st.markdown("*Fatture ricevute dai fornitori*")
        if st.button("**INIZIA →**", key="passiva_go", use_container_width=True):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Passiva"
            st.rerun()
    
# FORM FATTURAZIONE - VERSIONE CORRETTA
elif st.session_state.pagina == "form":
    st.image("logo.png", use_column_width=False)
    
    tipo = st.session_state.tipo
    st.header(f"📄 {tipo} - Nuova Fattura")
    
    # Form in due colonne
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data", value=datetime.now())
        numero = st.text_input("Numero Protocollo", value=f"2026/{len(st.session_state.dati_fatture[tipo])+1}")
        nome = st.text_input("Cliente/Fornitore", value="" if tipo == "Attiva" else "Fornitore")
        piva = st.text_input("P.IVA / CF", value="")
    
    with col2:
        imponibile = st.number_input("Imponibile (€)", min_value=0.0, step=0.01, format="%.2f")
        iva_perc = st.number_input("Aliquota IVA (%)", min_value=0.0, value=22.0, step=0.1)
        pagamento = st.selectbox("Modalità Pagamento", ["Bonifico 30gg", "Bonifico 60gg", "Anticipo", "Contanti"])
    
    # Calcolo totali
    iva, totale = calcola_totali(imponibile, iva_perc)
    col_tot1, col_tot2, _ = st.columns(3)
    col_tot1.metric("IVA", f"€ {iva:.2f}")
    col_tot2.metric("TOTALE", f"€ {totale:.2f}")
    
    note = st.text_area("Note", height=100)
    
    # === POPUP SALVATAGGIO (AL LIVELLO GIUSTO) ===
    @st.dialog(f"💾 Conferma salvataggio {tipo}", width="500")
    def dialog_salvataggio():
        st.markdown(f"**Confermi il salvataggio della fattura?**")
        st.markdown(f"### 📄 Dettagli:")
        st.markdown(f"- **Numero:** {numero}")
        st.markdown(f"- **Cliente/Fornitore:** {nome}")
        st.markdown(f"- **Totale:** € {totale:.2f}")
        
        col_c, col_s = st.columns([3,1])
        with col_c:
            if st.button("❌ **Annulla**", use_container_width=True):
                st.dialog_close()
        with col_s:
            if st.button("✅ **Salva**", type="primary", use_container_width=True):
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
                st.session_state.pagina = "storico"
                st.success("✅ Fattura salvata!")
                st.balloons()
                st.rerun()
    
    # Pulsanti azione
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("💾 **Salva Fattura**", type="primary", use_container_width=True):
            dialog_salvataggio()  # ← Chiamata corretta
    
    with col_btn2:
        if st.button("⬅️ Indietro", use_container_width=True):
            st.session_state.pagina = "home"
            st.rerun()
    
    with col_btn3:
        if st.button("🖨️ Stampa PDF", use_container_width=True):
            st.info("📄 PDF pronto!")


# STORICO FATTURE (SEZIONE AGGIORNATA)
elif st.session_state.pagina == "storico":
    
    # LOGO - sostituisci "logo.png" con il nome del tuo file
    st.image("logo1.png", use_column_width=False)
    
    st.header("📋 Storico Fatture")
    
    # Statistiche
    col1, col2 = st.columns(2)
    totale_attive = sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Attiva'])
    
    col1.metric("Fatture Attive", len(st.session_state.dati_fatture["Attiva"]))
    col2.metric("Totale Attivo", f"€ {totale_attive:.2f}")

    if st.button("📊 **Esporta TUTTE Attive in Excel**", type="primary", use_container_width=True):
        df = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
        buffer = create_excel_buffer(df, "Fatture_Attive")
        st.download_button(
            label="💾 Scarica Excel Attive",
            data=buffer,
            file_name=f"Fatture_Attive_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    st.markdown("---")

    col1, col2 = st.columns(2)
    totale_passive = sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Passiva'])
    col1.metric("Fatture Passive", len(st.session_state.dati_fatture["Passiva"]))
    col2.metric("Totale Passivo", f"€ {totale_passive:.2f}")

    if st.button("📊 **Esporta TUTTE Passive in Excel**", type="secondary", use_container_width=True):
        df = pd.DataFrame(st.session_state.dati_fatture["Passiva"])
        buffer = create_excel_buffer(df, "Fatture_Passive")
        st.download_button(
            label="💾 Scarica Excel Passive",
            data=buffer,
            file_name=f"Fatture_Passive_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.markdown("---")

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
                    data=create_excel_buffer(df_passive, "Fatture_Passive"),
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

# PAGINA ANAGRAFICHE
elif st.session_state.pagina == "anagrafiche":
    st.image("logo1.png", use_column_width=False)
    st.header("👥 **Gestione Anagrafiche**")
    
    st.markdown("### 📋 **Clienti**")
    if st.button("➕ **Nuovo Cliente**", use_container_width=True):
        st.info("Funzionalità in sviluppo...")
    
    st.markdown("### 📋 **Fornitori**")  
    if st.button("➕ **Nuovo Fornitore**", use_container_width=True):
        st.info("Funzionalità in sviluppo...")
    
    st.markdown("### 📊 **Elenco Completo**")
    col1, col2 = st.columns(2)
    col1.button("👁️ **Visualizza Clienti**", use_container_width=True)
    col2.button("👁️ **Visualizza Fornitori**", use_container_width=True)
    
    st.markdown("---")
    if st.button("⬅️ **Torna Indietro**", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()

