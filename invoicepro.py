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

def fattura_to_xml(fattura, tipo):
    """Converte singola fattura JSON → XML FatturaPA semplificato"""
    import xml.etree.ElementTree as ET
    from xml.dom import minidom
    
    # Root elemento
    fattura_xml = ET.Element("Fattura", tipo=tipo)
    
    # Dati generali
    generali = ET.SubElement(fattura_xml, "Generale")
    ET.SubElement(generali, "Data").text = fattura["data"]
    ET.SubElement(generali, "Numero").text = fattura["numero"]
    ET.SubElement(generali, "Totale").text = f"{fattura['totale']:.2f}"
    
    # Cliente/Fornitore
    controparte = ET.SubElement(fattura_xml, "Controparte")
    ET.SubElement(controparte, "RagioneSociale").text = fattura["cliente_fornitore"]
    ET.SubElement(controparte, "PIVA").text = fattura["piva"]
    
    # Importi
    importi = ET.SubElement(fattura_xml, "Importi")
    ET.SubElement(importi, "Imponibile").text = f"{fattura['imponibile']:.2f}"
    ET.SubElement(importi, "IVA").text = f"{fattura['iva']:.2f}"
    ET.SubElement(importi, "IVA_Perc").text = f"{fattura['iva_perc']}%"
    
    # Pagamento
    ET.SubElement(fattura_xml, "Pagamento").text = fattura["pagamento"]
    
    # Note
    ET.SubElement(fattura_xml, "Note").text = fattura["note"]
    
    # Pretty print XML
    rough_string = ET.tostring(fattura_xml, 'unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def esporta_fatture_xml(tipo_fatture):
    """Esporta TUTTE le fatture in un unico file XML"""
    import xml.etree.ElementTree as ET
    from xml.dom import minidom
    
    root = ET.Element("Fatture")
    for fattura in st.session_state.dati_fatture[tipo_fatture]:
        fattura_xml = ET.fromstring(fattura_to_xml(fattura, tipo_fatture[0].upper()))
        root.append(fattura_xml)
    
    rough_string = ET.tostring(root, 'unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ").encode('utf-8')

# 🔄 FUNZIONI ANAGRAFICHE (AGGIUNGI dopo create_excel_buffer)
def carica_anagrafiche():
    if os.path.exists("anagrafiche.json"):
        with open("anagrafiche.json", "r") as f:
            return json.load(f)
    return {"clienti": [], "fornitori": []}

def salva_anagrafiche(dati):
    with open("anagrafiche.json", "w") as f:
        json.dump(dati, f, indent=4, ensure_ascii=False)

# Inizializza anagrafiche
if 'anagrafiche' not in st.session_state:
    st.session_state.anagrafiche = carica_anagrafiche()

# PAGINA ANAGRAFICHE COMPLETA
elif st.session_state.pagina == "anagrafiche":
    st.image("banner1.png", use_column_width=False)
    st.header("👥 **Gestione Anagrafiche**")
    
    # Tabs per tipo
    tab1, tab2 = st.tabs(["➕ **NUOVO CLIENTE**", "➕ **NUOVO FORNITORE**"])
    
    with tab1:  # CLIENTE
        st.markdown("### 📝 **Dati Cliente**")
        with st.form("form_cliente"):
            col1, col2 = st.columns(2)
            with col1:
                rag_sociale = st.text_input("**Ragione Sociale**", placeholder="Mario Rossi Srl")
                nome_rapp = st.text_input("**Nome Rappresentante**", placeholder="Mario Rossi")
                piva = st.text_input("**P.IVA**", placeholder="IT12345678901")
                cf = st.text_input("**Codice Fiscale**", placeholder="RSSMRA80A01H501Z")
            with col2:
                indirizzo = st.text_input("**Indirizzo**", placeholder="Via Roma 123")
                cap = st.text_input("**CAP**", placeholder="00100")
                citta = st.text_input("**Città**", placeholder="Roma")
                prov = st.selectbox("**Provincia**", ["RM", "MI", "NA", "TO", "FI"])
                tel = st.text_input("**Telefono**", placeholder="06-1234567")
                email = st.text_input("**Email**", placeholder="info@mariorossi.it")
            
            col_submit, col_cancel = st.columns([3,1])
            with col_submit:
                submitted = st.form_submit_button("💾 **SALVA CLIENTE**", type="primary")
            with col_cancel:
                if st.form_submit_button("❌ **ANNULLA**"):
                    st.rerun()
            
            if submitted and rag_sociale:
                nuovo_cliente = {
                    "ragione_sociale": rag_sociale,
                    "rappresentante": nome_rapp,
                    "piva": piva,
                    "cf": cf,
                    "indirizzo": indirizzo,
                    "cap": cap,
                    "citta": citta,
                    "provincia": prov,
                    "telefono": tel,
                    "email": email,
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state.anagrafiche["clienti"].append(nuovo_cliente)
                salva_anagrafiche(st.session_state.anagrafiche)
                st.success("✅ **Cliente salvato!**")
                st.balloons()
                st.rerun()
    
    with tab2:  # FORNITORE  
        st.markdown("### 📝 **Dati Fornitore**")
        with st.form("form_fornitore"):
            col1, col2 = st.columns(2)
            with col1:
                rag_sociale_f = st.text_input("**Ragione Sociale**", placeholder="Fornitore XYZ")
                nome_rapp_f = st.text_input("**Nome Rappresentante**", placeholder="Luca Verdi")
                piva_f = st.text_input("**P.IVA**", placeholder="IT98765432109")
                cf_f = st.text_input("**Codice Fiscale**", placeholder="VRDL CU85M12L219X")
            with col2:
                indirizzo_f = st.text_input("**Indirizzo**", placeholder="Via Milano 456")
                cap_f = st.text_input("**CAP**", placeholder="20100")
                citta_f = st.text_input("**Città**", placeholder="Milano")
                prov_f = st.selectbox("**Provincia**", ["RM", "MI", "NA", "TO", "FI"])
                tel_f = st.text_input("**Telefono**", placeholder="02-9876543")
                email_f = st.text_input("**Email**", placeholder="ordini@fornitorexyz.it")
            
            col_submit_f, col_cancel_f = st.columns([3,1])
            with col_submit_f:
                submitted_f = st.form_submit_button("💾 **SALVA FORNITORE**", type="primary")
            with col_cancel_f:
                if st.form_submit_button("❌ **ANNULLA**"):
                    st.rerun()
            
            if submitted_f and rag_sociale_f:
                nuovo_fornitore = {
                    "ragione_sociale": rag_sociale_f,
                    "rappresentante": nome_rapp_f,
                    "piva": piva_f,
                    "cf": cf_f,
                    "indirizzo": indirizzo_f,
                    "cap": cap_f,
                    "citta": citta_f,
                    "provincia": prov_f,
                    "telefono": tel_f,
                    "email": email_f,
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state.anagrafiche["fornitori"].append(nuovo_fornitore)
                salva_anagrafiche(st.session_state.anagrafiche)
                st.success("✅ **Fornitore salvato!**")
                st.balloons()
                st.rerun()
    
    # ELENCO ANAGRAFICHE
    st.markdown("---")
    st.subheader("📋 **Elenco Anagrafiche**")
    
    col_list1, col_list2 = st.columns(2)
    
    with col_list1:
        st.markdown("**🏢 CLIENTI**")
        if st.session_state.anagrafiche["clienti"]:
            for i, cliente in enumerate(st.session_state.anagrafiche["clienti"][:10]):
                with st.expander(f"{cliente['ragione_sociale']} - {cliente['piva']}", expanded=False):
                    st.write(f"📧 {cliente['email']} | 📍 {cliente['citta']} ({cliente['provincia']})")
                    st.caption(f"Aggiunto: {cliente['timestamp'][:10]}")
        else:
            st.info("👆 Nessun cliente registrato")
    
    with col_list2:
        st.markdown("**🏭 FORNITORI**")
        if st.session_state.anagrafiche["fornitori"]:
            for i, fornitore in enumerate(st.session_state.anagrafiche["fornitori"][:10]):
                with st.expander(f"{fornitore['ragione_sociale']} - {fornitore['piva']}", expanded=False):
                    st.write(f"📧 {fornitore['email']} | 📍 {fornitore['citta']} ({fornitore['provincia']})")
                    st.caption(f"Aggiunto: {fornitore['timestamp'][:10]}")
        else:
            st.info("👆 Nessun fornitore registrato")
    
    # Torna indietro
    if st.button("⬅️ **Torna al Menu Principale**", type="secondary"):
        st.session_state.pagina = "home"
        st.rerun()

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
# Inizializza stato FORM
if 'form_dati_salvati' not in st.session_state:
    st.session_state.form_dati_salvati = False
if 'form_dati_temp' not in st.session_state:
    st.session_state.form_dati_temp = {}

# ✅ SIDEBAR (CORRETTA - all'inizio dopo init)
st.sidebar.title("📊 **CONFIGURAZIONE**")
anni = list(range(2020, 2051))
anno_selezionato = st.sidebar.selectbox("📅 **Anno Fatture**", anni, index=anni.index(2026))
st.sidebar.markdown("---")

if st.sidebar.button("🏠 **FATTURAZIONE**", use_container_width=True):
    st.session_state.pagina = "home"
st.sidebar.markdown("---")
if st.sidebar.button("📋 **ARCHIVIO FATTURE**", use_container_width=True):
    st.session_state.pagina = "storico"
st.sidebar.markdown("---")
if st.sidebar.button("👥 **ANAGRAFICHE**", use_container_width=True):
    st.session_state.pagina = "anagrafiche"
st.sidebar.info(f"**Anno: {anno_selezionato}**")
st.sidebar.markdown("---")

# ✅ HOME (CON if)
if st.session_state.pagina == "home":
    st.image("banner1.png", use_column_width=False)
    st.title("💼 Fatturazione aziendale 💼")
    st.markdown("---")
    
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
    
# FORM FATTURAZIONE CON CONTROLLO SALVATAGGIO
elif st.session_state.pagina == "form":
    st.image("banner1.png", use_column_width=False)
    tipo = st.session_state.tipo
    st.header(f"📄 {tipo} - Nuova Fattura")
    
    # === SALVA DATI TEMPORANEI in tempo reale ===
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data", value=datetime.now())
        numero = st.text_input("Numero Protocollo", value=f"2026/{len(st.session_state.dati_fatture[tipo])+1}")
        nome = st.text_input("Cliente/Fornitore", value="Cliente" if tipo == "Attiva" else "Fornitore")
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
    
    # === SALVA DATI TEMPORANEI ===
    st.session_state.form_dati_temp = {
        "data": data.strftime("%d/%m/%Y"),
        "numero": numero, 
        "cliente_fornitore": nome,
        "piva": piva,
        "imponibile": float(imponibile),
        "iva_perc": float(iva_perc),
        "iva": float(iva),
        "totale": float(totale),
        "pagamento": pagamento,
        "note": note
    }
    
    # === POPUP SALVATAGGIO ===
    @st.dialog("💾 Conferma salvataggio", width="500")
    def dialog_salvataggio():
        st.markdown("**⚠️ SALVA PRIMA di uscire dal form!**")
        st.markdown(f"### 📄 Dettagli fattura:")
        st.markdown(f"- **Numero:** {st.session_state.form_dati_temp['numero']}")
        st.markdown(f"- **Cliente:** {st.session_state.form_dati_temp['cliente_fornitore']}")
        st.markdown(f"- **Totale:** € {st.session_state.form_dati_temp['totale']:.2f}")
        
        col_c, col_s = st.columns([3,1])
        with col_c:
            if st.button("❌ **Annulla**", use_container_width=True):
                st.dialog_close()
        with col_s:
            if st.button("✅ **SALVA DEFINITIVO**", type="primary", use_container_width=True):
                # SALVA in fatture.json
                fattura = st.session_state.form_dati_temp.copy()
                fattura["timestamp"] = datetime.now().isoformat()
                st.session_state.dati_fatture[tipo].append(fattura)
                salva_dati(st.session_state.dati_fatture)
                
                # ✅ IMPOSTA SALVATO
                st.session_state.form_dati_salvati = True
                st.session_state.pagina = "storico"
                st.success("✅ Fattura salvata permanentemente!")
                st.balloons()
                st.rerun()
    
    # === PULSANTI CON CONTROLLO SALVATAGGIO ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💾 **SALVA**", type="primary", use_container_width=True):
            dialog_salvataggio()
    
    with col2:
        if st.button("⬅️ **Indietro**", use_container_width=True):
            if st.session_state.form_dati_salvati:
                st.session_state.pagina = "home"
                st.rerun()
            else:
                st.error("⚠️ **SALVA PRIMA** i dati inseriti!")
    
    with col3:
        if st.button("🖨️ **PDF**", use_container_width=True):
            if st.session_state.form_dati_salvati:
                st.info("📄 PDF generato!")
            else:
                st.error("⚠️ **SALVA PRIMA** la fattura!")
    
    with col4:
        if st.button("📄 **XML**", use_container_width=True):
            if st.session_state.form_dati_salvati:
                # Genera XML singolo
                xml_data = fattura_to_xml(st.session_state.form_dati_temp, tipo)
                st.download_button(
                    label="💾 Scarica XML",
                    data=xml_data,
                    file_name=f"{numero}_{tipo}.xml",
                    mime="application/xml"
                )
            else:
                st.error("⚠️ **SALVA PRIMA** la fattura!")
    
    # === INDICATORE STATO ===
    stato = "🟢 SALVATO" if st.session_state.form_dati_salvati else "🟡 NON SALVATO"
    st.metric("📝 Stato form", stato)

# STORICO FATTURE (SEZIONE AGGIORNATA)
elif st.session_state.pagina == "storico":
    
    # LOGO - sostituisci "logo.png" con il nome del tuo file
    st.image("banner1.png", use_column_width=False)
    
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
                    data=create_excel_buffer(df_attive, "Fatture_Attive"),
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

# Bottoni XML (AGGIUNGI dopo Excel)
col_xml1, col_xml2 = st.columns(2)

with col_xml1:
    xml_attive = esporta_fatture_xml("Attiva")
    st.download_button(
        label="📄 **XML Attive**",
        data=xml_attive,
        file_name=f"Fatture_Attive_{datetime.now().strftime('%Y%m%d_%H%M')}.xml",
        mime="application/xml",
        use_container_width=True
    )

with col_xml2:
    xml_passive = esporta_fatture_xml("Passiva")
    st.download_button(
        label="📄 **XML Passive**", 
        data=xml_passive,
        file_name=f"Fatture_Passive_{datetime.now().strftime('%Y%m%d_%H%M')}.xml",
        mime="application/xml",
        use_container_width=True
    )

# PAGINA ANAGRAFICHE
if st.session_state.pagina == "anagrafiche":
    st.image("banner1.png", use_column_width=False)
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

