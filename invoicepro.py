import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom
import base64

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
        'show_pdf_preview': False,
        'anno_selezionato': 2026
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

def carica_dati_sicuro():
    """Caricamento sicuro con validazione"""
    try:
        if os.path.exists("fatture.json"):
            with open("fatture.json", "r", encoding='utf-8') as f:
                dati = json.load(f)
                if isinstance(dati, dict) and "Attiva" in dati and "Passiva" in dati:
                    return dati
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

def crea_pdf_fattura_semplice(dati_fattura, tipo="Attiva"):
    """Simulazione PDF - testo formattato"""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 2px solid #1e3a8a;">
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <div style="width: 80px; height: 30px; background: #1e3a8a; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 20px;">
                LOGO
            </div>
            <h1 style="color: #1e3a8a; margin: 0; font-size: 28px;">FATTURA {tipo}</h1>
        </div>
        
        <hr style="border: 2px solid #1e3a8a; margin: 20px 0;">
        
        <div style="text-align: center; margin: 20px 0;">
            <h3>Data: {dati_fattura["data"]} | Nº: {dati_fattura["numero"]}</h3>
        </div>
        
        <div style="margin: 20px 0;">
            <h3 style="color: #1e3a8a;">{'CLIENTE' if tipo == 'Attiva' else 'FORNITORE'}</h3>
            <p style="font-size: 16px; margin: 5px 0;">{dati_fattura["cliente_fornitore"]}</p>
            <p style="font-size: 16px; margin: 5px 0;">P.IVA: {dati_fattura["piva"]}</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background: #e5e7eb;">
                    <th style="border: 1px solid #d1d5db; padding: 12px; text-align: center;">IMPONIBILE</th>
                    <th style="border: 1px solid #d1d5db; padding: 12px; text-align: center;">IVA</th>
                    <th style="border: 1px solid #d1d5db; padding: 12px; text-align: center;">IVA €</th>
                    <th style="border: 1px solid #d1d5db; padding: 12px; text-align: center;">TOTALE €</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="border: 1px solid #d1d5db; padding: 12px; text-align: right;">€ {dati_fattura["imponibile"]:>8.2f}</td>
                    <td style="border: 1px solid #d1d5db; padding: 12px; text-align: center;">{dati_fattura["iva_perc"]:.1f}%</td>
                    <td style="border: 1px solid #d1d5db; padding: 12px; text-align: right;">€ {dati_fattura["iva"]:>8.2f}</td>
                    <td style="border: 1px solid #d1d5db; padding: 12px; text-align: right; font-weight: bold; background: #fef3c7;">€ {dati_fattura["totale"]:>8.2f}</td>
                </tr>
            </tbody>
        </table>
        
        <div style="margin: 20px 0;">
            <strong>PAGAMENTO:</strong> {dati_fattura["pagamento"]}
        </div>
        
        {f'<div style="margin: 20px 0;"><strong>NOTE:</strong> {dati_fattura["note"]}</div>' if dati_fattura.get("note") else ""}
        
        <hr style="border: 1px solid #d1d5db; margin: 30px 0 20px 0;">
        <p style="text-align: center; color: #6b7280; font-size: 12px;">
            Generato con InvoicePro il {datetime.now().strftime("%d/%m/%Y %H:%M")}
        </p>
    </div>
    """
    return html

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

def create_excel_buffer(df, sheet_name):
    """Excel/CSV robusto"""
    if 'data' in df.columns:
        df = df.copy()
        df['data'] = df['data'].apply(formatta_data_df)
    
    buffer = io.BytesIO()
    try:
        import openpyxl
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        buffer.seek(0)
        return buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"
    except:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8')
        return csv_buffer.getvalue().encode('utf-8'), "text/csv", ".csv"

# =============================================================================
# CONFIGURAZIONE APP
# =============================================================================

st.set_page_config(
    page_title="Invoice Pro",
    page_icon="💼",
    layout="wide"
)

init_session_state()

# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.title("📊 **CONFIGURAZIONE**")
anni = list(range(2020, 2051))
st.session_state.anno_selezionato = st.sidebar.selectbox("📅 **Anno Fatture**", anni, index=anni.index(2026))

if st.sidebar.button("🏠 **FATTURAZIONE**", use_container_width=True):
    st.session_state.pagina = "home"
    st.rerun()

if st.sidebar.button("📋 **ARCHIVIO FATTURE**", use_container_width=True):
    st.session_state.pagina = "storico"
    st.rerun()

if st.sidebar.button("👥 **ANAGRAFICHE**", use_container_width=True):
    st.session_state.pagina = "anagrafiche"
    st.rerun()

st.sidebar.info(f"**Anno: {st.session_state.anno_selezionato}**")

# =============================================================================
# PAGINE
# =============================================================================

if st.session_state.pagina == "home":
    t.image("banner1.png", use_column_width=False)
    st.title("💼 **Fatturazione Aziendale** 💼")
    st.markdown("---")
    
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("### 🟢 **FATTURE ATTIVE**")
        if st.button("**➕ INIZIA NUOVA**", key="attiva_go", use_container_width=True):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Attiva"
            st.session_state.form_dati_salvati = False
            st.rerun()
    
    with col2:
        st.markdown("### 🔵 **FATTURE PASSIVE**")
        if st.button("**➕ INIZIA NUOVA**", key="passiva_go", use_container_width=True):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Passiva"
            st.session_state.form_dati_salvati = False
            st.rerun()

elif st.session_state.pagina == "form":
    tipo = st.session_state.tipo
    st.image("banner1.png", use_column_width=False)
    st.header(f"📄 **Nuova Fattura {tipo}**")
    
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("**📅 Data**", value=datetime.now())
        numero = st.text_input("**🔢 Numero Protocollo**", 
                              value=f"{st.session_state.anno_selezionato}/{len(st.session_state.dati_fatture[tipo])+1}")
        nome = st.text_input("**👤 Cliente/Fornitore**")
        piva = st.text_input("**🆔 P.IVA / CF**")
    
    with col2:
        imponibile = st.number_input("**💰 Imponibile (€)**", min_value=0.0, step=0.01, format="%.2f")
        iva_perc = st.number_input("**📊 Aliquota IVA (%)**", min_value=0.0, value=22.0, step=0.1)
        pagamento = st.selectbox("**💳 Modalità Pagamento**", 
                               ["Bonifico 30gg", "Bonifico 60gg", "Anticipo", "Contanti", "Ri.Ba.", "Bonifico immediato"])
    
    iva, totale = calcola_totali(imponibile, iva_perc)
    col_tot1, col_tot2 = st.columns(2)
    col_tot1.metric("**IVA**", f"€ {iva:.2f}")
    col_tot2.metric("**TOTALE**", f"€ {totale:.2f}")
    
    note = st.text_area("**📝 Note**", height=100)
    
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
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💾 **SALVA**", type="primary"):
            errori = valida_fattura(st.session_state.form_dati_temp)
            if errori:
                for errore in errori:
                    st.error(errore)
            else:
                fattura = st.session_state.form_dati_temp.copy()
                fattura["timestamp"] = datetime.now().isoformat()
                st.session_state.dati_fatture[tipo].append(fattura)
                salva_dati(st.session_state.dati_fatture)
                st.session_state.form_dati_salvati = True
                st.session_state.pagina = "storico"
                st.success("✅ Fattura salvata!")
                st.balloons()
                st.rerun()
    with col2:
        if st.button("⬅️ **Home**"):
            st.session_state.pagina = "home"
            st.rerun()
    with col3:
        if st.button("👁️ **ANTEPRIMA**"):
            st.session_state.show_pdf_preview = True
            st.rerun()
    with col4:
        xml_data = fattura_to_xml(st.session_state.form_dati_temp, tipo)
        st.download_button(
            label="📄 **XML**",
            data=xml_data,
            file_name=f"{st.session_state.form_dati_temp['numero']}_{tipo}.xml",
            mime="application/xml"
        )
    
    if st.session_state.get('show_pdf_preview', False):
        st.markdown("---")
        st.subheader("👀 **ANTEPRIMA FATTURA**")
        html_preview = crea_pdf_fattura_semplice(st.session_state.form_dati_temp, tipo)
        st.markdown(html_preview, unsafe_allow_html=True)
        
        if st.button("✕ **Chiudi Anteprima**", type="secondary"):
            st.session_state.show_pdf_preview = False
            st.rerun()

elif st.session_state.pagina == "storico":
    st.image("banner1.png", use_column_width=False)
    st.header("📋 **Archivio Fatture**")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fatture Attive", len(st.session_state.dati_fatture["Attiva"]))
    col2.metric("Totale Attivo", f"€ {sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Attiva']):.2f}")
    col3.metric("Fatture Passive", len(st.session_state.dati_fatture["Passiva"]))
    col4.metric("Totale Passivo", f"€ {sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Passiva']):.2f}")
    
    tab1, tab2 = st.tabs(["📤 Attiva", "📥 Passiva"])
    
    with tab1:
        if st.session_state.dati_fatture["Attiva"]:
            df = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            df['data'] = df['data'].apply(formatta_data_df)
            buffer_data, mime_type, file_ext = create_excel_buffer(df, "Fatture_Attive")
            col1, col2 = st.columns(2)
            col1.download_button("⬇️ Excel", data=buffer_data, file_name=f"Attive_{datetime.now().strftime('%Y%m%d')}{file_ext}", mime=mime_type)
            csv_data = df.to_csv(index=False, sep=';', encoding='utf-8').encode('utf-8')
            col2.download_button("📄 CSV", data=csv_data, file_name=f"Attive_{datetime.now().strftime('%Y%m%d')}.csv", mime='text/csv')
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna fattura attiva")
    
    with tab2:
        if st.session_state.dati_fatture["Passiva"]:
            df = pd.DataFrame(st.session_state.dati_fatture["Passiva"])
            df['data'] = df['data'].apply(formatta_data_df)
            buffer_data, mime_type, file_ext = create_excel_buffer(df, "Fatture_Passive")
            col1, col2 = st.columns(2)
            col1.download_button("⬇️ Excel", data=buffer_data, file_name=f"Passive_{datetime.now().strftime('%Y%m%d')}{file_ext}", mime=mime_type)
            csv_data = df.to_csv(index=False, sep=';', encoding='utf-8').encode('utf-8')
            col2.download_button("📄 CSV", data=csv_data, file_name=f"Passive_{datetime.now().strftime('%Y%m%d')}.csv", mime='text/csv')
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna fattura passiva")
    
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()

elif st.session_state.pagina == "anagrafiche":
    st.image("banner1.png", use_column_width=False)
    st.header("👥 **Anagrafiche**")
    
    tab1, tab2 = st.tabs(["➕ Cliente", "➕ Fornitore"])
    
    with tab1:
        with st.form("cliente"):
            col1, col2 = st.columns(2)
            with col1:
                rag_sociale = st.text_input("Ragione Sociale")
                piva = st.text_input("P.IVA")
            with col2:
                email = st.text_input("Email")
                telefono = st.text_input("Telefono")
            
            if st.form_submit_button("💾 Salva", type="primary"):
                if rag_sociale and piva:
                    if valida_piva(piva):
                        cliente = {
                            "ragione_sociale": rag_sociale.strip(),
                            "piva": piva.strip(),
                            "email": email.strip(),
                            "telefono": telefono.strip(),
                            "timestamp": datetime.now().isoformat()
                        }
                        st.session_state.anagrafiche["clienti"].append(cliente)
                        salva_anagrafiche(st.session_state.anagrafiche)
                        st.success("Cliente salvato!")
                        st.rerun()
                    else:
                        st.error("P.IVA non valida")
                else:
                    st.error("Compila tutti i campi")
    
    with tab2:
        with st.form("fornitore"):
            col1, col2 = st.columns(2)
            with col1:
                rag_sociale_f = st.text_input("Ragione Sociale")
                piva_f = st.text_input("P.IVA")
            with col2:
                email_f = st.text_input("Email")
                telefono_f = st.text_input("Telefono")
            
            if st.form_submit_button("💾 Salva", type="primary"):
                if rag_sociale_f and piva_f:
                    if valida_piva(piva_f):
                        fornitore = {
                            "ragione_sociale": rag_sociale_f.strip(),
                            "piva": piva_f.strip(),
                            "email": email_f.strip(),
                            "telefono": telefono_f.strip(),
                            "timestamp": datetime.now().isoformat()
                        }
                        st.session_state.anagrafiche["fornitori"].append(fornitore)
                        salva_anagrafiche(st.session_state.anagrafiche)
                        st.success("Fornitore salvato!")
                        st.rerun()
                    else:
                        st.error("P.IVA non valida")
                else:
                    st.error("Compila tutti i campi")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 Clienti")
        for c in st.session_state.anagrafiche["clienti"]:
            st.write(f"**{c['ragione_sociale']}** - {c['piva']}")
    
    with col2:
        st.subheader("🏭 Fornitori")
        for f in st.session_state.anagrafiche["fornitori"]:
            st.write(f"**{f['ragione_sociale']}** - {f['piva']}")
    
    if st.button("⬅️ Home", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()
