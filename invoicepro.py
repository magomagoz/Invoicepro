import streamlit as st
import json
import os
import pandas as pd
import io
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

# =============================================================================
# INIZIALIZZAZIONE SESSION STATE (SENZA LIBRERIE ESTERNE)
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
    defaults = {
        'dati_fatture': {"Attiva": [], "Passiva": []},
        'anagrafiche': {"clienti": [], "fornitori": []},
        'pagina': 'home',
        'form_dati_salvati': False,
        'form_dati_temp': {},
        'tipo': None,
        'show_pdf_preview': False,
        'anno_selezionato': 2026
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Carica/Salva dati
def carica_dati():
    if os.path.exists("fatture.json"):
        try:
            with open("fatture.json", "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"Attiva": [], "Passiva": []}

def carica_anagrafiche():
    if os.path.exists("anagrafiche.json"):
        try:
            with open("anagrafiche.json", "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"clienti": [], "fornitori": []}

def salva_dati(dati):
    try:
        with open("fatture.json", "w", encoding='utf-8') as f:
            json.dump(dati, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False

def salva_anagrafiche(dati):
    try:
        with open("anagrafiche.json", "w", encoding='utf-8') as f:
            json.dump(dati, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False

# Aggiorna dati persistenti
st.session_state.dati_fatture = carica_dati()
st.session_state.anagrafiche = carica_anagrafiche()

# =============================================================================
# FUNZIONI UTILITY (SOLO LIBRERIE BASE)
# =============================================================================
def calcola_totali(imponibile, iva_perc):
    try:
        imp = float(imponibile or 0)
        iva_p = float(iva_perc or 0) / 100
        iva = imp * iva_p
        totale = imp + iva
        return round(iva, 2), round(totale, 2)
    except:
        return 0.0, 0.0

def valida_piva(piva):
    piva = piva.replace("IT", "").replace(" ", "").strip().upper()
    return len(piva) == 11 and piva.isdigit()

def valida_cf(cf):
    cf = cf.replace("IT", "").replace(" ", "").strip().upper()
    return len(cf) == 16 and cf.isalnum()

def valida_fattura(dati):
    errori = []
    if not dati.get("cliente_fornitore", "").strip():
        errori.append("❌ Cliente/Fornitore obbligatorio")
    if not dati.get("piva", "").strip():
        errori.append("❌ P.IVA/CF obbligatorio")
    elif not valida_piva(dati["piva"]):
        errori.append("❌ P.IVA non valida (11 cifre)")
    if float(dati.get("imponibile", 0)) <= 0:
        errori.append("❌ Imponibile > 0")
    if not dati.get("numero", "").strip():
        errori.append("❌ Numero protocollo obbligatorio")
    return errori

def cancella_storico():
    risposta = messagebox.askyesno("Conferma", "Eliminare TUTTE le fatture dallo storico?")
    if risposta:
        storico_fatture.clear()  # Svuota lista
        # Oppure: apri file e sovrascrivi con lista vuota
        salva_storico([])  
        messagebox.showinfo("Fatto", "Storico cancellato!")
        aggiorna_lista_archivio()  # Ricarica interfaccia

def formatta_data_df(data_str):
    try:
        if pd.isna(data_str) or data_str == "":
            return ""
        if isinstance(data_str, str) and '/' in data_str:
            return data_str
        dt = pd.to_datetime(data_str)
        return dt.strftime("%d/%m/%Y")
    except:
        return str(data_str)

import base64

def fattura_to_xml(fattura, tipo):
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

# =============================================================================
# SIDEBAR
# =============================================================================
st.sidebar.title("📊 **CONFIGURAZIONE**")
anni = list(range(2020, 2051))
st.session_state.anno_selezionato = st.sidebar.selectbox(
    "📅 **Anno Fatture**", 
    anni, 
    index=anni.index(2026)
)
st.sidebar.info(f"**Anno selezionato: {st.session_state.anno_selezionato}**")

st.sidebar.markdown("---")
if st.sidebar.button("🏠 **FATTURAZIONE**", use_container_width=True):
    st.session_state.pagina = "home"
    st.rerun()

if st.sidebar.button("📋 **ARCHIVIO FATTURE**", use_container_width=True):
    st.session_state.pagina = "storico"
    st.rerun()

if st.sidebar.button("👥 **ANAGRAFICHE**", use_container_width=True):
    st.session_state.pagina = "anagrafiche"
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("📈 **ANALISI RICAVI/COSTI**", use_container_width=True, type="secondary"):
    st.session_state.pagina = "analisi"
    st.rerun()
# =============================================================================
# PAGINE PRINCIPALI (SENZA SPAZI VUOTI)
# =============================================================================
if st.session_state.pagina == "home":
    st.image("banner1.png", use_column_width=False, caption="Invoice Pro")
    st.title("💼 **Fatturazione Aziendale** 💼")
    st.markdown("---")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("### 🟢 **FATTURE ATTIVE**")
        st.markdown("*Fatture emesse ai clienti*")
        if st.button("**➕ INIZIA NUOVA**", key="attiva_go", use_container_width=True, type="secondary"):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Attiva"
            st.session_state.form_dati_salvati = False
            st.session_state.form_dati_temp = {}
            st.rerun()
    
    with col2:
        st.markdown("### 🔵 **FATTURE PASSIVE**")
        st.markdown("*Fatture ricevute dai fornitori*")
        if st.button("**➕ INIZIA NUOVA**", key="passiva_go", use_container_width=True, type="secondary"):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Passiva"
            st.session_state.form_dati_salvati = False
            st.session_state.form_dati_temp = {}
            st.rerun()

elif st.session_state.pagina == "form":
    tipo = st.session_state.tipo
    st.image("banner1.png", use_column_width=False)
    st.header(f"📄 **Nuova Fattura {tipo}**")
    
    # Form principale
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        data = st.date_input("**📅 Data**", 
                            value=datetime.now(),
                            format="DD/MM/YYYY")
        anno_selezionato = st.session_state.anno_selezionato
        numero = st.text_input("**🔢 Numero Fattura**", 
                              value=f"{anno_selezionato}/{len(st.session_state.dati_fatture[tipo])+1}")
        nome = st.text_input("**👤 Cliente/Fornitore**", value="" if tipo == "Attiva" else "")
        piva = st.text_input("**🆔 P.IVA / CF**", value="")
    
    with col2:
        imponibile = st.number_input("**💰 Imponibile (€)**", min_value=0.0, step=0.01, format="%.2f")
        iva_perc = st.number_input("**📊 Aliquota IVA (%)**", min_value=0.0, value=22.0, step=0.1)
        pagamento = st.selectbox("**💳 Modalità Pagamento**", 
                               ["Bonifico 30gg", "Bonifico 60gg", "Anticipo", "Contanti", "Ri.Ba.", "Bonifico immediato"])
        # ← CAMPO SCADENZA AGGIUNTO
        scadenza = st.date_input("**⏰ Data Scadenza**", 
                               value=datetime.now() + pd.Timedelta(days=30),  # 30gg da oggi
                               min_value=datetime.now(), 
                               format="DD/MM/YYYY")
    
    # Totali
    iva, totale = calcola_totali(imponibile, iva_perc)
    col_tot1, col_tot2 = st.columns(2)
    col_tot1.metric("**IVA**", f"€ {iva:.2f}")
    col_tot2.metric("**TOTALE**", f"€ {totale:.2f}")
    
    note = st.text_area("**📝 Note**", height=100)
    
    # Salva dati temporanei
    st.session_state.form_dati_temp = {
        "data": data.strftime("%d/%m/%Y"),
        "numero": numero.strip(),
        "cliente_fornitore": nome.strip(),
        "piva": piva.strip(),
        "imponibile": float(imponibile),
        "iva_perc": float(iva_perc),
        "iva": float(iva),
        "totale": float(totale),
        "pagamento": pagamento,
        "note": note.strip(),
        "scadenza": scadenza.strftime("%d/%m/%Y"),  # ← AGGIUNTO
        'analisi': {}  # ← AGGIUNGI QUESTA RIGA
    }

    # Pulsanti azione con validazione
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💾 **SALVA**", type="primary", use_container_width=True):
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
                st.success("✅ **Fattura salvata con successo!**")
                st.balloons()
                st.rerun()
    
    with col2:
        if st.button("⬅️ **Home**", use_container_width=True):
            if st.session_state.form_dati_salvati or st.button("Confermi uscita senza salvare?"):
                st.session_state.pagina = "home"
                st.session_state.form_dati_salvati = False
                st.rerun()
            else:
                st.error("⚠️ **SALVA prima** i dati inseriti!")
    
    with col3:
        if st.button("📄 **XML**", use_container_width=True):
            xml_data = fattura_to_xml(st.session_state.form_dati_temp, tipo)
            st.download_button(
                label="💾 **Scarica XML**",
                data=xml_data.encode('utf-8'),
                file_name=f"{st.session_state.form_dati_temp['numero']}_{tipo}.xml",
                mime="application/xml",
                use_container_width=True
            )
    
    # Indicatore stato
    stato = "🟢 **SALVATO**" if st.session_state.form_dati_salvati else "🟡 **NON SALVATO**"
    st.metric("📝 **Stato form**", stato)
    
elif st.session_state.pagina == "storico":
    st.image("banner1.png", use_column_width=False)
    st.header("📋 **Archivio Fatture**")
    
    # Statistiche
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📤 Fatture Attive", len(st.session_state.dati_fatture["Attiva"]))
    col2.metric("💶 Totale Attivo", f"€ {sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Attiva']):.2f}")
    col3.metric("📥 Fatture Passive", len(st.session_state.dati_fatture["Passiva"]))
    col4.metric("💸 Totale Passivo", f"€ {sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Passiva']):.2f}")
    
    # Tabs
    tab1, tab2 = st.tabs(["📤 **Fatturazione Attiva**", "📥 **Fatturazione Passiva**"])
    
    with tab1:
        if st.session_state.dati_fatture["Attiva"]:
            df_attive = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            df_attive['data'] = df_attive['data'].apply(formatta_data_df)
            
            csv_data = df_attive.to_csv(index=False, sep=';', encoding='utf-8').encode('utf-8')
            st.download_button(
                label="📄 **CSV Attive**",
                data=csv_data,
                file_name=f"Fatture_Attive_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
                mime='text/csv',
                use_container_width=True
            )

            if st.button(
                label="Cancella Storico Attive e Passive", 
                key="cancella_attive",
                use_container_width=True, 
                type="secondary"
            ):
                st.session_state.confirm_delete_attive = True
            
            if st.session_state.get("confirm_delete_attive", False):
                col1, col2 = st.columns([3,1])
                with col1:
                    st.error("⚠️ CONFERMI cancellazione TUTTE le fatture attive e passive?")
                with col2:
                    if st.button("SI, CANCELLA", key="si_attive", type="primary"):
                        st.session_state.dati_fatture["Attiva"] = []
                        if os.path.exists("fatture.json"):
                            os.remove("fatture.json")
                        st.session_state.confirm_delete_attive = False
                        st.success("✅ Storico attive cancellato!")
                        st.rerun()
                    if st.button("ANNULLA", key="no_attive"):
                        st.session_state.confirm_delete_attive = False
                        st.rerun()


            st.dataframe(df_attive, use_container_width=True, hide_index=True)
        else:
            st.info("👆 **Nessuna fattura attiva**. Crea la prima dalla Home!")
    
    with tab2:
        if st.session_state.dati_fatture["Passiva"]:
            df_passive = pd.DataFrame(st.session_state.dati_fatture["Passiva"])
            df_passive['data'] = df_passive['data'].apply(formatta_data_df)

            # Bottone esportazione
            csv_data = df_passive.to_csv(index=False, sep=';', encoding='utf-8').encode('utf-8')
            st.download_button(
                label="📄 **CSV Passive**",
                data=csv_data,
                file_name=f"Fatture_Passive_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
                mime='text/csv',
                use_container_width=True
            )

            if st.button(
                label="Cancella Storico Attive e Passive", 
                key="cancella_attive",
                use_container_width=True, 
                type="secondary"
            ):
                st.session_state.confirm_delete_attive = True
            
            if st.session_state.get("confirm_delete_attive", False):
                col1, col2 = st.columns([3,1])
                with col1:
                    st.error("⚠️ CONFERMI cancellazione TUTTE le fatture attive e passive?")
                with col2:
                    if st.button("SI, CANCELLA", key="si_attive", type="primary"):
                        st.session_state.dati_fatture["Attiva"] = []
                        if os.path.exists("fatture.json"):
                            os.remove("fatture.json")
                        st.session_state.confirm_delete_attive = False
                        st.success("✅ Storico attive cancellato!")
                        st.rerun()
                    if st.button("ANNULLA", key="no_attive"):
                        st.session_state.confirm_delete_attive = False
                        st.rerun()


            st.dataframe(df_passive, use_container_width=True, hide_index=True)
        else:
            st.info("👆 **Nessuna fattura passiva**. Crea la prima dalla Home!")
    
    if st.button("🏠 **Torna alla Home**", type="secondary", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()

elif st.session_state.pagina == "analisi":
    st.image("banner1.png", use_column_width=True)
    st.header("📈 **Analisi Ricavi, Costi e Scadenze**")
    
    # STATISTICHE GENERALI
    col1, col2, col3, col4 = st.columns(4)
    totali_attive = sum(f.get('totale', 0) for f in st.session_state.dati_fatture["Attiva"])
    totali_passive = sum(f.get('totale', 0) for f in st.session_state.dati_fatture["Passiva"])
    
    col1.metric("💰 **RICAVI TOTALI**", f"€ {totali_attive:,.2f}")
    col2.metric("💸 **COSTI TOTALI**", f"€ {totali_passive:,.2f}")
    col3.metric("📊 **GUADAGNO**", f"€ {totali_attive - totali_passive:,.2f}", 
                delta=f"{((totali_attive/totali_passive)-1)*100:.1f}%" if totali_passive > 0 else "∞")
    mesi_it = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile", 5: "Maggio", 6: "Giugno",
    7: "Luglio", 8: "Agosto", 9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
    }
    mese_nome = mesi_it[datetime.now().month]
    col4.metric("📅 **MESE CORRENTE**", f"{mese_nome} {datetime.now().year}")

    #col4.metric("📅 **OGGI**", datetime.now().strftime("%d/%m/%Y"))
    
    st.markdown("---")
    
    # ANALISI SCADENZE
    oggi = datetime.now().date()
    
    # Fatture ATTIVE da incassare
    attive_scadute = []
    attive_ok = []
    for f in st.session_state.dati_fatture["Attiva"]:
        if 'scadenza' in f:
            scadenza = datetime.strptime(f['scadenza'], "%d/%m/%Y").date()
            if scadenza < oggi:
                attive_scadute.append(f)
            else:
                attive_ok.append(f)
    
    # Fatture PASSIVE da pagare  
    passive_scadute = []
    passive_ok = []
    for f in st.session_state.dati_fatture["Passiva"]:
        if 'scadenza' in f:
            scadenza = datetime.strptime(f['scadenza'], "%d/%m/%Y").date()
            if scadenza < oggi:
                passive_scadute.append(f)
            else:
                passive_ok.append(f)
    
    # VISUALIZZAZIONE SCADENZE
    col_scad1, col_scad2 = st.columns(2)
    
    with col_scad1:
        st.markdown("### 🚨 **SCADUTE**")
        if attive_scadute:
            st.error(f"**{len(attive_scadute)} fatture attive scadute**")
            for f in attive_scadute[:5]:  # Prime 5
                giorni = (oggi - datetime.strptime(f['scadenza'], "%d/%m/%Y").date()).days
                st.warning(f"• {f['numero']} - €{f['totale']:.2f} ({giorni}gg)")
        else:
            st.success("✅ Nessuna attiva scaduta")
            
        if passive_scadute:
            st.error(f"**{len(passive_scadute)} fatture passive scadute**")
            for f in passive_scadute[:5]:
                giorni = (oggi - datetime.strptime(f['scadenza'], "%d/%m/%Y").date()).days
                st.warning(f"• {f['numero']} - €{f['totale']:.2f} ({giorni}gg)")
        else:
            st.success("✅ Nessuna passiva scaduta")
    
    with col_scad2:
        st.markdown("### ✅ **PAGATE**")
        st.info(f"**{len(attive_ok)} attive da incassare**")
        st.info(f"**{len(passive_ok)} passive da pagare**")
    
    # TABELLA COMPLETA SCADENZE
    if attive_scadute or passive_scadute:
        st.markdown("---")
        st.subheader("📋 **DETTAGLIO SCADENZE**")
        
        dati_scadenze = []
        for f in attive_scadute + passive_scadute:
            scadenza_date = datetime.strptime(f['scadenza'], "%d/%m/%Y").date()
            giorni = (oggi - scadenza_date).days
            dati_scadenze.append({
                "Tipo": "ATTIVA ❌" if f in attive_scadute else "PASSIVA ❌",
                "Numero": f['numero'],
                "Cliente": f['cliente_fornitore'][:20] + "...",
                "Importo": f"€{f['totale']:.2f}",
                "Scadenza": f['scadenza'],
                "Giorni": f"{giorni}gg"
            })
        
        if dati_scadenze:
            df_scadenze = pd.DataFrame(dati_scadenze)
            st.dataframe(df_scadenze, use_container_width=True)
    
    # TORNA INDIETRO
    if st.button("⬅️ **Torna alla Home**", type="secondary", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()

elif st.session_state.pagina == "anagrafiche":
    st.image("banner1.png", use_column_width=False)
    st.header("👥 **Gestione Anagrafiche**")
    
    # Tabs per nuovi inserimenti
    tab1, tab2 = st.tabs(["➕ **Nuovo Cliente**", "➕ **Nuovo Fornitore**"])
    
    with tab1:
        st.markdown("### 📝 **Dati Cliente**")
        with st.form("form_cliente"):
            col1, col2 = st.columns(2)
            with col1:
                rag_sociale = st.text_input("**Ragione Sociale**", placeholder="Mario Rossi Srl")
                piva = st.text_input("**P.IVA**", placeholder="IT12345678901")
            with col2:
                email = st.text_input("**Email**", placeholder="info@mariorossi.it")
                telefono = st.text_input("**Telefono**", placeholder="06-1234567")
            
            col_submit, col_cancel = st.columns([3, 1])
            with col_submit:
                submitted = st.form_submit_button("💾 **SALVA CLIENTE**", type="primary")
            with col_cancel:
                if st.form_submit_button("❌ **ANNULLA**"):
                    st.rerun()
            
            if submitted and rag_sociale and piva:
                if valida_piva(piva):
                    nuovo_cliente = {
                        "ragione_sociale": rag_sociale.strip(),
                        "piva": piva.strip(),
                        "email": email.strip(),
                        "telefono": telefono.strip(),
                        "timestamp": datetime.now().isoformat()
                    }
                    st.session_state.anagrafiche["clienti"].append(nuovo_cliente)
                    salva_anagrafiche(st.session_state.anagrafiche)
                    st.success("✅ **Cliente salvato con successo!**")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ **P.IVA non valida** (11 cifre numeriche)")
            elif submitted:
                st.error("❌ **Compila tutti i campi obbligatori**")
    
    with tab2:
        st.markdown("### 📝 **Dati Fornitore**")
        with st.form("form_fornitore"):
            col1, col2 = st.columns(2)
            with col1:
                rag_sociale_f = st.text_input("**Ragione Sociale**", placeholder="Fornitore XYZ")
                piva_f = st.text_input("**P.IVA**", placeholder="IT98765432109")
            with col2:
                email_f = st.text_input("**Email**", placeholder="ordini@xyz.it")
                telefono_f = st.text_input("**Telefono**", placeholder="02-9876543")
            
            col_submit_f, col_cancel_f = st.columns([3, 1])
            with col_submit_f:
                submitted_f = st.form_submit_button("💾 **SALVA FORNITORE**", type="primary")
            with col_cancel_f:
                if st.form_submit_button("❌ **ANNULLA**"):
                    st.rerun()
            
            if submitted_f and rag_sociale_f and piva_f:
                if valida_piva(piva_f):
                    nuovo_fornitore = {
                        "ragione_sociale": rag_sociale_f.strip(),
                        "piva": piva_f.strip(),
                        "email": email_f.strip(),
                        "telefono": telefono_f.strip(),
                        "timestamp": datetime.now().isoformat()
                    }
                    st.session_state.anagrafiche["fornitori"].append(nuovo_fornitore)
                    salva_anagrafiche(st.session_state.anagrafiche)
                    st.success("✅ **Fornitore salvato con successo!**")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ **P.IVA non valida** (11 cifre numeriche)")
            elif submitted_f:
                st.error("❌ **Compila tutti i campi obbligatori**")
    
    # Elenco anagrafiche
    st.markdown("---")
    st.subheader("📋 **Elenco Anagrafiche Salvate**")
    
    col_list1, col_list2 = st.columns(2)
    
    with col_list1:
        st.markdown("### 🏢 **CLIENTI**")
        if st.session_state.anagrafiche["clienti"]:
            for i, cliente in enumerate(st.session_state.anagrafiche["clienti"][:10]):
                with st.expander(f"**{cliente['ragione_sociale']}** - {cliente['piva']}", expanded=False):
                    st.write(f"📧 **{cliente.get('email', 'N/D')}**")
                    st.write(f"📞 **{cliente.get('telefono', 'N/D')}**")
                    st.caption(f"Aggiunto: {cliente['timestamp'][:10]}")
        else:
            st.info("👆 **Nessun cliente registrato**")
    
    with col_list2:
        st.markdown("### 🏭 **FORNITORI**")
        if st.session_state.anagrafiche["fornitori"]:
            for i, fornitore in enumerate(st.session_state.anagrafiche["fornitori"][:10]):
                with st.expander(f"**{fornitore['ragione_sociale']}** - {fornitore['piva']}", expanded=False):
                    st.write(f"📧 **{fornitore.get('email', 'N/D')}**")
                    st.write(f"📞 **{fornitore.get('telefono', 'N/D')}**")
                    st.caption(f"Aggiunto: {fornitore['timestamp'][:10]}")
        else:
            st.info("👆 **Nessun fornitore registrato**")
    
    if st.button("⬅️ **Torna alla Home**", type="secondary", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()
