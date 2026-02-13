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
import base64  # ✅ AGGIUNTO - essenziale per PDF
from fpdf import FPDF

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
        'tipo': None,
        'show_pdf_preview': False,  # ✅ AGGIUNTO
        'anno_selezionato': 2026    # ✅ AGGIUNTO
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
        st.success("✅ Dati salvati correttamente!")
    except Exception as e:
        st.error(f"❌ Errore salvataggio: {e}")

def salva_anagrafiche(dati):
    """Salva anagrafiche"""
    try:
        with open("anagrafiche.json", "w", encoding='utf-8') as f:
            json.dump(dati, f, indent=4, ensure_ascii=False)
        st.success("✅ Anagrafiche salvate!")
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

def crea_pdf_fattura(dati_fattura, tipo="Attiva"):
    """PDF professionale con LOGO + anteprima"""
    pdf = FPDF()
    pdf.add_page()
    
    # ✅ LOGO ALTO SINISTRA - ROBUSTO
    try:
        if os.path.exists("logo.png"):
            pdf.image("logo.png", x=10, y=6, w=32)
        else:
            # Fallback placeholder professionale
            pdf.set_font('Arial', 'B', 16)
            pdf.set_xy(10, 8)
            pdf.set_fill_color(30, 60, 120)
            pdf.cell(32, 8, 'LOGO', 0, 0, 'C', 1)
    except:
        pdf.set_font('Arial', 'B', 16)
        pdf.set_xy(10, 8)
        pdf.cell(32, 8, 'LOGO', 0, 0, 'C')
    
    # Titolo accanto al logo
    pdf.set_font('Arial', 'B', 22)
    pdf.set_xy(50, 8)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(140, 12, f'FATTURA {tipo}', ln=True)
    
    # Linea decorativa
    pdf.line(10, 30, 200, 30)
    
    # Dati fattura centrati
    pdf.set_xy(0, 35)
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f'Data: {dati_fattura["data"]}     Nº: {dati_fattura["numero"]}', 0, 1, 'C')
    
    # Cliente/Fornitore
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, 'CLIENTE' if tipo == "Attiva" else 'FORNITORE', 0, 1, 'L')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 7, dati_fattura["cliente_fornitore"], 0, 1, 'L')
    pdf.cell(0, 7, f'P.IVA: {dati_fattura["piva"]}', 0, 1, 'L')
    
    # Tabella importi professionale
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    
    # Header tabella
    pdf.cell(48, 8, 'IMPONIBILE', 1, 0, 'C', 1)
    pdf.cell(38, 8, 'IVA', 1, 0, 'C', 1)
    pdf.cell(48, 8, 'IVA €', 1, 0, 'C', 1)
    pdf.cell(48, 8, 'TOTALE €', 1, 1, 'C', 1)
    
    # Dati tabella
    pdf.set_font('Arial', '', 12)
    pdf.set_fill_color(255, 255, 255)
    pdf.cell(48, 8, f'€ {dati_fattura["imponibile"]:>8.2f}', 1, 0, 'R')
    pdf.cell(38, 8, f'{dati_fattura["iva_perc"]:.1f}%', 1, 0, 'C')
    pdf.cell(48, 8, f'€ {dati_fattura["iva"]:>8.2f}', 1, 0, 'R')
    pdf.cell(48, 8, f'€ {dati_fattura["totale"]:>8.2f}', 1, 1, 'R')
    
    # Pagamento
    pdf.ln(12)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 8, 'PAGAMENTO:', 0, 0)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, dati_fattura["pagamento"], 0, 1)
    
    # Note
    if dati_fattura.get("note"):
        pdf.ln(8)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(40, 8, 'NOTE:', 0, 0)
        pdf.set_font('Arial', '', 11)
        pdf.ln(6)
        pdf.multi_cell(0, 5, dati_fattura["note"])
    
    # Footer elegante
    pdf.ln(15)
    pdf.set_font('Arial', 'I', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f'Generato con InvoicePro il {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

def pdf_download_link(pdf_bytes, filename):
    """Link download PDF"""
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="application/pdf;base64,{b64}" download="{filename}.pdf" style="background:#2563eb;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;display:inline-block;margin:10px 0;">📥 SCARICA PDF</a>'
    return href

def create_excel_buffer(df, sheet_name):
    """Excel/CSV robusto - FUNZIONA SEMPRE"""
    # Formatta date
    if 'data' in df.columns:
        df = df.copy()
        df['data'] = df['data'].apply(formatta_data_df)
    
    buffer = io.BytesIO()
    
    # Prova Excel
    try:
        import openpyxl
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        buffer.seek(0)
        return buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"
    
    except:
        # CSV fallback (SEMPRE funzionante)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8')
        return csv_buffer.getvalue().encode('utf-8'), "text/csv", ".csv"

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
    ET.SubElement(fattura_xml, "Note").text = fattura["note"] or ""
    
    rough_string = ET.tostring(fattura_xml, 'unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def esporta_fatture_xml(tipo_fatture):
    """Esporta tutte le fatture in XML - ✅ FIXATO"""
    if not st.session_state.dati_fatture[tipo_fatture]:
        return b""
    
    root = ET.Element("Fatture")
    for fattura in st.session_state.dati_fatture[tipo_fatture]:
        xml_singola = fattura_to_xml(fattura, tipo_fatture.upper())  # ✅ CORRETTO
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
st.session_state.anno_selezionato = st.sidebar.selectbox("📅 **Anno Fatture**", anni, index=anni.index(2026))
st.sidebar.markdown("---")

if st.sidebar.button("🏠 **FATTURAZIONE**", use_container_width=True):
    st.session_state.pagina = "home"
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("📋 **ARCHIVIO FATTURE**", use_container_width=True):
    st.session_state.pagina = "storico"
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("👥 **ANAGRAFICHE**", use_container_width=True):
    st.session_state.pagina = "anagrafiche"
    st.rerun()

st.sidebar.info(f"**Anno: {st.session_state.anno_selezionato}**")
st.sidebar.markdown("---")

# =============================================================================
# PAGINE PRINCIPALI
# =============================================================================

if st.session_state.pagina == "home":
    # Banner placeholder se non esiste
    try:
        st.image("banner1.png", use_column_width=False)
    except:
        st.markdown("![Banner](https://via.placeholder.com/1200x200/1e3a8a/ffffff?text=INVOICE+PRO)")
    
    st.title("💼 **Fatturazione Aziendale** 💼")
    st.markdown("---")
    
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("### 🟢 **FATTURE ATTIVE**")
        st.markdown("*Fatture emesse ai clienti*")
        if st.button("**➕ INIZIA NUOVA**", key="attiva_go", use_container_width=True):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Attiva"
            st.session_state.form_dati_salvati = False
            st.session_state.show_pdf_preview = False
            st.rerun()
    
    with col2:
        st.markdown("### 🔵 **FATTURE PASSIVE**")
        st.markdown("*Fatture ricevute dai fornitori*")
        if st.button("**➕ INIZIA NUOVA**", key="passiva_go", use_container_width=True):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Passiva"
            st.session_state.form_dati_salvati = False
            st.session_state.show_pdf_preview = False
            st.rerun()

elif st.session_state.pagina == "form":
    try:
        st.image("banner1.png", use_column_width=False)
    except:
        st.markdown("![Banner](https://via.placeholder.com/1200x200/1e3a8a/ffffff?text=INVOICE+PRO)")
    
    tipo = st.session_state.tipo
    st.header(f"📄 **Nuova Fattura {tipo}**")
    
    # Form principale
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("**📅 Data**", value=datetime.now(), format="DD/MM/YYYY")
        numero = st.text_input("**🔢 Numero Protocollo**", 
                              value=f"{st.session_state.anno_selezionato}/{len(st.session_state.dati_fatture[tipo])+1}")
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
            if st.button("❌ **Annulla**", use_container_width=True):
                st.dialog_close()
        with col_s:
            if st.button("✅ **SALVA DEFINITIVO**", type="primary", use_container_width=True):
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
        if st.button("💾 **SALVA**", type="primary"):
            dialog_salvataggio()
    with col2:
        if st.button("⬅️ **Home**"):
            st.session_state.pagina = "home"
            st.rerun()
    with col3:
        if st.button("👁️ **ANTEPRIMA PDF**"):
            st.session_state.show_pdf_preview = True
            st.rerun()
    with col4:
        # ✅ XML SEMPRE disponibile
        if st.session_state.form_dati_temp:
            xml_data = fattura_to_xml(st.session_state.form_dati_temp, tipo)
            st.download_button(
                label="📄 **XML**",
                data=xml_data,
                file_name=f"{st.session_state.form_dati_temp['numero']}_{tipo}.xml",
                mime="application/xml"
            )
    
    # Indicatore stato
    stato = "🟢 **SALVATO**" if st.session_state.form_dati_salvati else "🟡 **NON SALVATO**"
    st.metric("📝 **Stato Form**", stato)

    # SEZIONE ANTEPRIMA PDF
    if st.session_state.get('show_pdf_preview', False):
        st.markdown("---")
        st.subheader("👀 **ANTEPRIMA PDF**")
        
        with st.spinner("Generando PDF..."):
            pdf_bytes = crea_pdf_fattura(st.session_state.form_dati_temp, st.session_state.tipo)
            
            # ANTEPRIMA INTERATTIVA
            pdf_base64 = base64.b64encode(pdf_bytes).decode()
            st.markdown(
                f"""
                <div style="border: 3px solid #e5e7eb; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
                    <iframe src="application/pdf;base64,{pdf_base64}" 
                            width="100%" height="700px" 
                            style="border: none; display: block;">
                    </iframe>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        # Download
        st.markdown(pdf_download_link(pdf_bytes, st.session_state.form_dati_temp['numero']), unsafe_allow_html=True)
        
        if st.button("✕ **Chiudi Anteprima**", type="secondary"):
            st.session_state.show_pdf_preview = False
            st.rerun()
    
elif st.session_state.pagina == "storico":
    try:
        st.image("banner1.png", use_column_width=False)
    except:
        st.markdown("![Banner](https://via.placeholder.com/1200x200/1e3a8a/ffffff?text=INVOICE+PRO)")
    
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
        if st.session_state.dati_fatture["Attiva"]:
            df = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            buffer_data, mime_type, file_ext = create_excel_buffer(df, "Fatture_Attive")
            st.download_button(
                label="📊 **Excel/CSV Attive**",
                data=buffer_data,
                file_name=f"Fatture_Attive_{datetime.now().strftime('%Y%m%d')}{file_ext}",
                mime=mime_type
            )
    
    with col_ex2:
        xml_attive = esporta_fatture_xml("Attiva")
        if xml_attive:
            st.download_button(
                label="📄 **XML Attive Complete**",
                data=xml_attive,
                file_name=f"Fatture_Attive_{datetime.now().strftime('%Y%m%d_%H%M')}.xml",
                mime="application/xml"
            )
    
    st.markdown("---")
    
    # Tabs per tipo
    tab1, tab2 = st.tabs(["📤 **Fatturazione Attiva**", "📥 **Fatturazione Passiva**"])
    
    with tab1:
        if st.session_state.dati_fatture["Attiva"]:
            df_attive = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            df_attive['data'] = df_attive['data'].apply(formatta_data_df)
            
            col1, col2 = st.columns(2)
            with col1:
                buffer_data, mime_type, file_ext = create_excel_buffer(df_attive, "Fatture_Attive")
                st.download_button(
                    label="⬇️ **Excel**",
                    data=buffer_data,
                    file_name=f"Attive_{datetime.now().strftime('%Y%m%d_%H%M')}{file_ext}",
                    mime=mime_type
                )
            with col2:
                csv_data = df_attive.to_csv(index=False, sep=';', encoding='utf-8').encode('utf-8')
                st.download_button(
                    label="📄 **CSV**",
                    data=csv_data,
                    file_name=f"Attive_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv'
                )
            
            st.dataframe(df_attive, use_container_width=True, hide_index=True)
        else:
            st.info("👆 **Nessuna fattura attiva**. Crea la prima!")
    
    with tab2:
        if st.session_state.dati_fatture["Passiva"]:
            df_passive = pd.DataFrame(st.session_state.dati_fatture["Passiva"])
            df_passive['data'] = df_passive['data'].apply(formatta_data_df)
            
            col1, col2 = st.columns(2)
            with col1:
                buffer_data, mime_type, file_ext = create_excel_buffer(df_passive, "Fatture_Passive")
                st.download_button(
                    label="⬇️ **Excel**",
                    data=buffer_data,
                    file_name=f"Passive_{datetime.now().strftime('%Y%m%d_%H%M')}{file_ext}",
                    mime=mime_type
                )
            with col2:
                csv_data = df_passive.to_csv(index=False, sep=';', encoding='utf-8').encode('utf-8')
                st.download_button(
                    label="📄 **CSV**",
                    data=csv_data,
                    file_name=f"Passive_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv'
                )
            
            st.dataframe(df_passive, use_container_width=True, hide_index=True)
        else:
            st.info("👆 **Nessuna fattura passiva**.")
    
    if st.button("🏠 **Torna alla Home**", type="secondary", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()

elif st.session_state.pagina == "anagrafiche":
    try:
        st.image("banner1.png", use_column_width=False)
    except:
        st.markdown("![Banner](https://via.placeholder.com/1200x200/1e3a8a/ffffff?text=INVOICE+PRO)")
    
    st.header("👥 **Gestione Anagrafiche Complete**")
    
    # Tabs per tipo
    tab1, tab2 = st.tabs(["➕ **NUOVO CLIENTE**", "➕ **NUOVO FORNITORE**"])
    
    with tab1:
        st.markdown("### 📝 **Dati Cliente**")
        with st.form("form_cliente"):
            col1, col2 = st.columns(2)
            with col1:
                rag_sociale = st.text_input("**Ragione Sociale**")
                nome_rapp = st.text_input("**Nome Rappresentante**")
                piva = st.text_input("**P.IVA**")
                cf = st.text_input("**Codice Fiscale**")
            with col2:
                indirizzo = st.text_input("**Indirizzo**")
                cap = st.text_input("**CAP**")
                citta = st.text_input("**Città**")
                prov = st.selectbox("**Provincia**", ["RM", "LT", "RI", "VT", "FI", "BO", "FR", "AQ"])
                tel = st.text_input("**Telefono**")
                email = st.text_input("**Email**")
            
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
                rag_sociale_f = st.text_input("**Ragione Sociale**")
                nome_rapp_f = st.text_input("**Nome Rappresentante**")
                piva_f = st.text_input("**P.IVA**")
                cf_f = st.text_input("**Codice Fiscale**")
            with col2:
                indirizzo_f = st.text_input("**Indirizzo**")
                cap_f = st.text_input("**CAP**")
                citta_f = st.text_input("**Città**")
                prov_f = st.selectbox("**Provincia**", ["RM", "LT", "RI", "VT", "FI", "BO", "FR", "AQ"])
                tel_f = st.text_input("**Telefono**")
                email_f = st.text_input("**Email**")
            
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
    
    if st.button("⬅️ **Torna al Menu Principale**", type="secondary", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()
