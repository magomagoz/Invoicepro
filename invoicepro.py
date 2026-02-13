import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import json
import os
from datetime import datetime
import pandas as pd
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom

# =============================================================================
# FUNZIONI UTILITY
# =============================================================================

def formatta_data_df(data_str):
    """Converte data per dataframe in dd/mm/yyyy"""
    try:
        if pd.isna(data_str):
            return ""
        if isinstance(data_str, str) and '/' in data_str:
            return data_str
        dt = pd.to_datetime(data_str)
        return dt.strftime("%d/%m/%Y")
    except:
        return str(data_str)

def init_session_state():
    """Inizializza tutto lo stato dell'applicazione"""
    defaults = {
        'dati_fatture': carica_dati_sicuro(),
        'pagina': 'home',
        'anagrafiche': carica_anagrafiche(),
        'form_dati_salvati': False,
        'form_dati_temp': {},
        'tipo': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def valida_piva(piva):
    """Validazione P.IVA italiana semplificata"""
    piva = piva.replace("IT", "").replace(" ", "").strip().upper()
    return len(piva) == 11 and piva.isdigit()

def valida_fattura(dati):
    """Controlla i dati della fattura prima del salvataggio"""
    errori = []
    if not dati.get("cliente_fornitore", "").strip():
        errori.append("❌ Cliente/Fornitore obbligatorio")
    if not dati.get("piva", "").strip():
        errori.append("❌ P.IVA/CF obbligatorio")
    elif not valida_piva(dati["piva"]):
        errori.append("❌ P.IVA non valida (11 cifre numeriche)")
    if float(dati.get("imponibile", 0)) <= 0:
        errori.append("❌ Imponibile deve essere > 0")
    if not dati.get("numero", "").strip():
        errori.append("❌ Numero protocollo obbligatorio")
    return errori

def valida_anagrafica(tipo, dati):
    """Validazione anagrafiche"""
    errori = []
    if not dati.get("ragione_sociale", "").strip():
        errori.append("❌ Ragione sociale obbligatoria")
    if not dati.get("piva", "").strip():
        errori.append("❌ P.IVA obbligatoria")
    elif not valida_piva(dati["piva"]):
        errori.append("❌ P.IVA non valida")
    
    # Controllo duplicati
    anagrafiche = st.session_state.anagrafiche
    piva = dati["piva"].strip()
    if tipo == "clienti":
        if any(c["piva"] == piva for c in anagrafiche["clienti"]):
            errori.append("❌ P.IVA cliente già esistente")
    else:
        if any(f["piva"] == piva for f in anagrafiche["fornitori"]):
            errori.append("❌ P.IVA fornitore già esistente")
    return errori

def carica_dati_sicuro():
    """Caricamento sicuro con validazione"""
    try:
        if os.path.exists("fatture.json"):
            with open("fatture.json", "r", encoding='utf-8') as f:
                dati = json.load(f)
                if isinstance(dati, dict) and "Attiva" in dati and "Passiva" in dati:
                    return dati
                st.error("❌ File fatture.json corrotto. Creo nuovo file.")
    except Exception:
        pass
    return {"Attiva": [], "Passiva": []}

def carica_anagrafiche():
    """Carica anagrafiche con fallback"""
    try:
        if os.path.exists("anagrafiche.json"):
            with open("anagrafiche.json", "r", encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {"clienti": [], "fornitori": []}

def salva_dati(dati):
    """Salva fatture con gestione errori"""
    try:
        with open("fatture.json", "w", encoding='utf-8') as f:
            json.dump(dati, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"❌ Errore salvataggio: {e}")

def salva_anagrafiche(dati):
    """Salva anagrafiche"""
    try:
        with open("anagrafiche.json", "w", encoding='utf-8') as f:
            json.dump(dati, f, indent=4, ensure_ascii=False)
    except:
        st.error("❌ Errore salvataggio anagrafiche")

def calcola_totali(imponibile, iva_perc):
    """Calcola IVA e totale"""
    try:
        imp = float(imponibile or 0)
        iva_p = float(iva_perc or 0) / 100
        iva = imp * iva_p
        totale = imp + iva
        return round(iva, 2), round(totale, 2)
    except:
        return 0.0, 0.0

def crea_pdf_fattura_semplice(dati_fattura, tipo="Attiva"):
    """PDF funzionante su Streamlit Cloud"""
    from fpdf import FPDF
    
    pdf = FPDF()
    pdf.add_page()

        # Logo dal repo (funziona su Streamlit Cloud)
    try:
        pdf.image("logo.png", x=10, y=6, w=30)  # Nel tuo repo
    except:
        # Fallback URL
        pdf.image("https://via.placeholder.com/120x40/2c3e50/ffffff?text=LOGO", x=10, y=6, w=30)

    
    
    pdf.set_font('Arial', 'B', 20)
    pdf.cell(0, 10, f'FATTURA {tipo}', ln=True, align='C')
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f'Data: {dati_fattura["data"]}', ln=True)
    pdf.cell(0, 8, f'Nº: {dati_fattura["numero"]}', ln=True)
    pdf.cell(0, 8, f'{dati_fattura["cliente_fornitore"]}', ln=True)
    pdf.cell(0, 8, f'P.IVA: {dati_fattura["piva"]}', ln=True)
    
    pdf.ln(10)
    pdf.cell(60, 8, f'€ {dati_fattura["imponibile"]:>10.2f}', 1)
    pdf.cell(45, 8, f'€ {dati_fattura["totale"]:>8.2f}', 1)
    
    pdf.output(dest='S').encode('latin-1')

def create_excel_buffer(df, sheet_name):
    """Excel con fallback CSV - Robusta"""
    buffer = io.BytesIO()
    
    # Prova Excel
    try:
        import openpyxl
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Formattazione solo se openpyxl funziona
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            
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
            
            from openpyxl.styles import Font
            for cell in worksheet[1]:
                cell.font = Font(bold=True)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    except (ImportError, Exception):
        # Fallback CSV professionale
        output = io.StringIO()
        df.to_csv(output, index=False, sep=';', decimal=',')
        csv_data = output.getvalue().encode('utf-8')
        return csv_data

def fattura_to_xml(fattura, tipo):
    """Converte fattura in XML FatturaPA semplificato"""
    fattura_xml = ET.Element("Fattura", tipo=tipo)
    
    generali = ET.SubElement(fattura_xml, "Generale")
    ET.SubElement(generali, "Data").text = fattura["data"]
    ET.SubElement(generali, "Numero").text = fattura["numero"]
    ET.SubElement(generali, "Totale").text = f"{fattura['totale']:.2f}"
    
    controparte = ET.SubElement(fattura_xml, "Controparte")
    ET.SubElement(controparte, "RagioneSociale").text = fattura["cliente_fornitore"]
    ET.SubElement(controparte, "PIVA").text = fattura["piva"]
    
    importi = ET.SubElement(fattura_xml, "Importi")
    ET.SubElement(importi, "Imponibile").text = f"{fattura['imponibile']:.2f}"
    ET.SubElement(importi, "IVA").text = f"{fattura['iva']:.2f}"
    ET.SubElement(importi, "IVA_Perc").text = f"{fattura['iva_perc']}%"
    
    ET.SubElement(fattura_xml, "Pagamento").text = fattura["pagamento"]
    ET.SubElement(fattura_xml, "Note").text = fattura["note"]
    
    rough_string = ET.tostring(fattura_xml, 'unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def esporta_fatture_xml(tipo_fatture):
    """Esporta tutte le fatture in XML"""
    if not st.session_state.dati_fatture[tipo_fatture]:
        return b""
    
    root = ET.Element("Fatture")
    for fattura in st.session_state.dati_fatture[tipo_fatture]:
        xml_singola = fattura_to_xml(fattura, tipo_fatture[0].upper())
        fattura_xml = ET.fromstring(xml_singola)
        root.append(fattura_xml)
    
    rough_string = ET.tostring(root, 'unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ").encode('utf-8')

# =============================================================================
# CONFIGURAZIONE APP
# =============================================================================

st.set_page_config(
    page_title="Invoice Pro",
    page_icon="💼",
    layout="wide"
)

# Inizializza stato
init_session_state()

# =============================================================================
# SIDEBAR NAVIGAZIONE
# =============================================================================

st.sidebar.title("📊 **CONFIGURAZIONE**")
anni = list(range(2020, 2051))
anno_selezionato = st.sidebar.selectbox("📅 **Anno Fatture**", anni, index=anni.index(2026))
st.sidebar.markdown("---")

if st.sidebar.button("🏠 **FATTURAZIONE**", use_container_width="stretch"):
    st.session_state.pagina = "home"
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("📋 **ARCHIVIO FATTURE**", use_container_width="stretch"):
    st.session_state.pagina = "storico"
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("👥 **ANAGRAFICHE**", use_container_width="stretch"):
    st.session_state.pagina = "anagrafiche"
    st.rerun()

st.sidebar.info(f"**Anno: {anno_selezionato}**")
st.sidebar.markdown("---")

# =============================================================================
# PAGINE PRINCIPALI
# =============================================================================

if st.session_state.pagina == "home":
    st.image("banner1.png", use_column_width=False)
    st.title("💼 **Fatturazione Aziendale** 💼")
    st.markdown("---")
    
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("### 🟢 **FATTURE ATTIVE**")
        st.markdown("*Fatture emesse ai clienti*")
        if st.button("**➕ INIZIA NUOVA**", key="attiva_go", use_container_width="stretch"):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Attiva"
            st.session_state.form_dati_salvati = False
            st.rerun()
    
    with col2:
        st.markdown("### 🔵 **FATTURE PASSIVE**")
        st.markdown("*Fatture ricevute dai fornitori*")
        if st.button("**➕ INIZIA NUOVA**", key="passiva_go", use_container_width="stretch"):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Passiva"
            st.session_state.form_dati_salvati = False
            st.rerun()

elif st.session_state.pagina == "form":
    st.image("banner1.png", use_column_width=False)
    tipo = st.session_state.tipo
    st.header(f"📄 **Nuova Fattura {tipo}**")
    
    # Form principale
    col1, col2 = st.columns(2)
    with col1:
        
        data = st.date_input("**📅 Data**", value=datetime.now(), format="DD/MM/YYYY")
        numero = st.text_input("**🔢 Numero Protocollo**", 
                              value=f"{anno_selezionato}/{len(st.session_state.dati_fatture[tipo])+1}")
        nome = st.text_input("**👤 Cliente/Fornitore**", value="" if tipo == "Attiva" else "Fornitore")
        piva = st.text_input("**🆔 P.IVA / CF**", value="")
    
    with col2:
        imponibile = st.number_input("**💰 Imponibile (€)**", min_value=0.0, step=0.01, format="%.2f")
        iva_perc = st.number_input("**📊 Aliquota IVA (%)**", min_value=0.0, value=22.0, step=0.1)
        pagamento = st.selectbox("**💳 Modalità Pagamento**", 
                               ["Bonifico 30gg", "Bonifico 60gg", "Anticipo", "Contanti", "Ri.Ba.", "Bonifico immediato"])
    
    # Calcolo totali live
    iva, totale = calcola_totali(imponibile, iva_perc)
    col_tot1, col_tot2, _ = st.columns(3)
    col_tot1.metric("**IVA**", f"€ {iva:.2f}")
    col_tot2.metric("**TOTALE**", f"€ {totale:.2f}")
    
    note = st.text_area("**📝 Note**", height=100, placeholder="Eventuali note sulla fattura...")
    
    # Salva dati temporanei
    st.session_state.form_dati_temp = {
        "data": data.strftime("%d/%m/%Y"),
        "numero": numero,
        "cliente_fornitore": nome.strip(),
        "piva": piva.strip(),
        "imponibile": float(imponibile),
        "iva_perc": float(iva_perc),
        "iva": float(iva),
        "totale": float(totale),
        "pagamento": pagamento,
        "note": note.strip()
    }
    
    # Dialog conferma salvataggio
    @st.dialog("💾 **Conferma Salvataggio**", width="500")
    def dialog_salvataggio():
        st.markdown("**⚠️ Verifica i dati prima di salvare!**")
        dati_temp = st.session_state.form_dati_temp
        st.markdown(f"""
        ### 📄 **Riepilogo Fattura:**
        - **Numero:** {dati_temp['numero']}
        - **Cliente:** {dati_temp['cliente_fornitore']}
        - **P.IVA:** {dati_temp['piva']}
        - **Totale:** € {dati_temp['totale']:.2f}
        """)
        
        col_c, col_s = st.columns([3,1])
        with col_c:
            if st.button("❌ **Annulla**", use_container_width="stretch"):
                st.dialog_close()
        with col_s:
            if st.button("✅ **SALVA DEFINITIVO**", type="primary", use_container_width="stretch"):
                # Validazione finale
                errori = valida_fattura(dati_temp)
                if errori:
                    for errore in errori:
                        st.error(errore)
                else:
                    # Salva
                    fattura = dati_temp.copy()
                    fattura["timestamp"] = datetime.now().isoformat()
                    st.session_state.dati_fatture[tipo].append(fattura)
                    salva_dati(st.session_state.dati_fatture)
                    st.session_state.form_dati_salvati = True
                    st.session_state.pagina = "storico"
                    st.success("✅ **Fattura salvata permanentemente!**")
                    st.balloons()
                    st.rerun()
    
    # Pulsanti azione
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💾 **SALVA**", type="primary", use_container_width="stretch"):
            dialog_salvataggio()
    
    with col2:
        if st.button("⬅️ **Indietro**", use_container_width="stretch"):
            if st.session_state.form_dati_salvati or st.button("Conferma uscita senza salvare", key="conferma_uscita"):
                st.session_state.pagina = "home"
                st.rerun()
            else:
                st.error("⚠️ **SALVA PRIMA** i dati inseriti!")
    
    with col3:
        if st.button("🖨️ **PDF**", use_container_width="stretch"):
            st.info("📄 PDF in sviluppo...")
    
    with col4:
        if st.button("📄 **XML**", use_container_width="stretch"):
            if st.session_state.form_dati_salvati:
                xml_data = fattura_to_xml(st.session_state.form_dati_temp, tipo)
                st.download_button(
                    label="💾 **Scarica XML**",
                    data=xml_data,
                    file_name=f"{st.session_state.form_dati_temp['numero']}_{tipo}.xml",
                    mime="application/xml"
                )
            else:
                st.error("⚠️ **SALVA PRIMA** la fattura!")
    
    # Indicatore stato
    stato = "🟢 **SALVATO**" if st.session_state.form_dati_salvati else "🟡 **NON SALVATO**"
    st.metric("📝 **Stato Form**", stato)

elif st.session_state.pagina == "storico":
    st.image("banner1.png", use_column_width=False)
    st.header("📋 **Archivio Fatture Complete**")
    
    # Statistiche generali
    col1, col2, col3, col4 = st.columns(4)
    totale_attive = sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Attiva'])
    totale_passive = sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Passiva'])
    
    col1.metric("**Fatture Attive**", len(st.session_state.dati_fatture["Attiva"]))
    col2.metric("**Totale Attivo**", f"€ {totale_attive:.2f}")
    col3.metric("**Fatture Passive**", len(st.session_state.dati_fatture["Passiva"]))
    col4.metric("**Totale Passivo**", f"€ {totale_passive:.2f}")
    
    # Bottoni export generali
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        # Per Excel buttons
        if st.session_state.dati_fatture["Attiva"]:
            df = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            buffer = create_excel_buffer(df, "Fatture_Attive")
            
            # Rileva tipo file dal buffer
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if len(buffer) > 1000 else "text/csv"
            file_ext = ".xlsx" if len(buffer) > 1000 else ".csv"
            
            st.download_button(
                label="📊 **Excel/CSV Attive**",
                data=buffer,
                file_name=f"Fatture_Attive_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"  # ✅ NUOVO PARAMETRO
            )
    
    with col_ex2:
        xml_attive = esporta_fatture_xml("Attiva")
        if xml_attive:
            st.download_button(
                label="📄 **XML Attive Complete**",
                data=xml_attive,
                file_name=f"Fatture_Attive_{datetime.now().strftime('%Y%m%d_%H%M')}.xml",
                mime="application/xml",
                use_container_width="stretch"
            )
    
    st.markdown("---")
    
    # Tabs per tipo
    tab1, tab2 = st.tabs(["📤 **Fatturazione Attiva**", "📥 **Fatturazione Passiva**"])
    
    with tab1:
        # Per Excel buttons
        if st.session_state.dati_fatture["Attiva"]:
            df = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            buffer = create_excel_buffer(df, "Fatture_Attive")
            
            # Rileva tipo file dal buffer
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if len(buffer) > 1000 else "text/csv"
            file_ext = ".xlsx" if len(buffer) > 1000 else ".csv"
            
            st.download_button(
                label="📊 **Excel/CSV Attive**",
                data=buffer,
                file_name=f"Fatture_Attive_{datetime.now().strftime('%Y%m%d')}{file_ext}",
                mime=mime_type,
                use_container_width="stretch"
            )

            with col2:
                csv = df_attive.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 **CSV**",
                    data=csv,
                    file_name=f"Attive_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv',
                    use_container_width="stretch"
                )

        # Prima di st.dataframe():
        if st.session_state.dati_fatture["Attiva"]:
            df_attive = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            df_attive['data'] = df_attive['data'].apply(formatta_data_df)
            
            st.dataframe(df_attive, use_container_width=True, hide_index=True)
        else:
            st.info("👆 **Nessuna fattura attiva**. Crea la prima dalla Home!")
    
    with tab2:
        # Per Excel buttons
        if st.session_state.dati_fatture["Attiva"]:
            df = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            buffer = create_excel_buffer(df, "Fatture_Attive")
            
            # Rileva tipo file dal buffer
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if len(buffer) > 1000 else "text/csv"
            file_ext = ".xlsx" if len(buffer) > 1000 else ".csv"
            
            st.download_button(
                label="📊 **Excel/CSV Attive**",
                data=buffer,
                file_name=f"Fatture_Attive_{datetime.now().strftime('%Y%m%d')}{file_ext}",
                mime=mime_type,
                use_container_width="stretch"
            )

            with col2:
                csv = df_passive.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 **CSV**",
                    data=csv,
                    file_name=f"Passive_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv',
                    use_container_width="stretch"
                )
            df_passive['data'] = df_passive['data'].apply(formatta_data_df)
            st.dataframe(df_passive, use_container_width=True, hide_index=True)
        else:
            st.info("👆 **Nessuna fattura passiva**. Crea la prima dalla Home!")
    
    if st.button("🏠 **Torna alla Home**", type="secondary", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()

elif st.session_state.pagina == "anagrafiche":
    st.image("banner1.png", use_column_width=False)
    st.header("👥 **Gestione Anagrafiche Complete**")
    
    # Tabs per tipo
    tab1, tab2 = st.tabs(["➕ **NUOVO CLIENTE**", "➕ **NUOVO FORNITORE**"])
    
    with tab1:
        st.markdown("### 📝 **Dati Cliente**")
        with st.form("form_cliente"):
            col1, col2 = st.columns(2)
            with col1:
                rag_sociale = st.text_input("**Ragione Sociale**", placeholder="")
                nome_rapp = st.text_input("**Nome Rappresentante**", placeholder="")
                piva = st.text_input("**P.IVA**", placeholder="")
                cf = st.text_input("**Codice Fiscale**", placeholder="")
            with col2:
                indirizzo = st.text_input("**Indirizzo**", placeholder="")
                cap = st.text_input("**CAP**", placeholder="")
                citta = st.text_input("**Città**", placeholder="")
                prov = st.selectbox("**Provincia**", ["RM", "LT", "RI", "VT", "FI", "BO", "FR", "AQ"])
                tel = st.text_input("**Telefono**", placeholder="")
                email = st.text_input("**Email**", placeholder="")
            
            col_submit, col_cancel = st.columns([3,1])
            with col_submit:
                submitted = st.form_submit_button("💾 **SALVA CLIENTE**", type="primary")
            with col_cancel:
                if st.form_submit_button("❌ **ANNULLA**"):
                    st.rerun()
            
            if submitted and rag_sociale:
                dati_cliente = {
                    "ragione_sociale": rag_sociale.strip(),
                    "rappresentante": nome_rapp.strip(),
                    "piva": piva.strip(),
                    "cf": cf.strip(),
                    "indirizzo": indirizzo.strip(),
                    "cap": cap.strip(),
                    "citta": citta.strip(),
                    "provincia": prov,
                    "telefono": tel.strip(),
                    "email": email.strip(),
                    "timestamp": datetime.now().isoformat()
                }
                
                errori = valida_anagrafica("clienti", dati_cliente)
                if errori:
                    for errore in errori:
                        st.error(errore)
                else:
                    st.session_state.anagrafiche["clienti"].append(dati_cliente)
                    salva_anagrafiche(st.session_state.anagrafiche)
                    st.success("✅ **Cliente salvato correttamente!**")
                    st.balloons()
                    st.rerun()
    
    with tab2:
        st.markdown("### 📝 **Dati Fornitore**")
        with st.form("form_fornitore"):
            col1, col2 = st.columns(2)
            with col1:
                rag_sociale_f = st.text_input("**Ragione Sociale**", placeholder="")
                nome_rapp_f = st.text_input("**Nome Rappresentante**", placeholder="")
                piva_f = st.text_input("**P.IVA**", placeholder="")
                cf_f = st.text_input("**Codice Fiscale**", placeholder="")
            with col2:
                indirizzo_f = st.text_input("**Indirizzo**", placeholder="")
                cap_f = st.text_input("**CAP**", placeholder="")
                citta_f = st.text_input("**Città**", placeholder="")
                prov_f = st.selectbox("**Provincia**", ["RM", "LT", "RI", "VT", "FI", "BO", "FR", "AQ"])
                tel_f = st.text_input("**Telefono**", placeholder="")
                email_f = st.text_input("**Email**", placeholder="")
            
            col_submit_f, col_cancel_f = st.columns([3,1])
            with col_submit_f:
                submitted_f = st.form_submit_button("💾 **SALVA FORNITORE**", type="primary")
            with col_cancel_f:
                if st.form_submit_button("❌ **ANNULLA**"):
                    st.rerun()
            
            if submitted_f and rag_sociale_f:
                dati_fornitore = {
                    "ragione_sociale": rag_sociale_f.strip(),
                    "rappresentante": nome_rapp_f.strip(),
                    "piva": piva_f.strip(),
                    "cf": cf_f.strip(),
                    "indirizzo": indirizzo_f.strip(),
                    "cap": cap_f.strip(),
                    "citta": citta_f.strip(),
                    "provincia": prov_f,
                    "telefono": tel_f.strip(),
                    "email": email_f.strip(),
                    "timestamp": datetime.now().isoformat()
                }
                
                errori = valida_anagrafica("fornitori", dati_fornitore)
                if errori:
                    for errore in errori:
                        st.error(errore)
                else:
                    st.session_state.anagrafiche["fornitori"].append(dati_fornitore)
                    salva_anagrafiche(st.session_state.anagrafiche)
                    st.success("✅ **Fornitore salvato correttamente!**")
                    st.balloons()
                    st.rerun()
    
    # Elenco anagrafiche
    st.markdown("---")
    st.subheader("📋 **Elenco Anagrafiche**")
    
    col_list1, col_list2 = st.columns(2)
    
    with col_list1:
        st.markdown("**🏢 CLIENTI**")
        if st.session_state.anagrafiche["clienti"]:
            for cliente in st.session_state.anagrafiche["clienti"][:10]:
                with st.expander(f"{cliente['ragione_sociale']} - {cliente['piva']}", expanded=False):
                    st.write(f"📧 {cliente['email']} | 📍 {cliente['citta']} ({cliente['provincia']})")
                    st.caption(f"Aggiunto: {cliente['timestamp'][:10]}")
        else:
            st.info("👆 **Nessun cliente registrato**")
    
    with col_list2:
        st.markdown("**🏭 FORNITORI**")
        if st.session_state.anagrafiche["fornitori"]:
            for fornitore in st.session_state.anagrafiche["fornitori"][:10]:
                with st.expander(f"{fornitore['ragione_sociale']} - {fornitore['piva']}", expanded=False):
                    st.write(f"📧 {fornitore['email']} | 📍 {fornitore['citta']} ({fornitore['provincia']})")
                    st.caption(f"Aggiunto: {fornitore['timestamp'][:10]}")
        else:
            st.info("👆 **Nessun fornitore registrato**")
    
    if st.button("⬅️ **Torna al Menu Principale**", type="secondary", use_container_width="stretch"):
        st.session_state.pagina = "home"
        st.rerun()
