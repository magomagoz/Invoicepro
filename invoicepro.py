import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd

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

# Layout principale con sidebar
st.title("💼 Gestione Fatturazione Attiva/Passiva")
st.markdown("---")

# Sidebar navigazione
st.sidebar.title("Navigazione")
if st.sidebar.button("🏠 Home - Scegli Tipo", use_container_width=True):
    st.session_state.pagina = "home"

if st.sidebar.button("📋 Storico Fatture", use_container_width=True):
    st.session_state.pagina = "storico"

# PAGINA HOME - Scelta tipo fatturazione
if st.session_state.pagina == "home":
    st.header("Scegli il tipo di fatturazione")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 **FATTURAZIONE ATTIVA**", 
                    type="primary", use_container_width=True, help="Fatture emesse ai clienti"):
            st.session_state.pagina = "form"
            st.session_state.tipo = "Attiva"
            st.rerun()
    
    with col2:
        if st.button("📥 **FATTURAZIONE PASSIVA**", 
                    type="secondary", use_container_width=True, help="Fatture ricevute dai fornitori"):
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
                           value="Mario Rossi Srl" if tipo == "Attiva" else "Fornitore XYZ")
        piva = st.text_input("P.IVA / CF", value="IT12345678901")
    
    with col2:
        imponibile = st.number_input("Imponibile (€)", min_value=0.0, value=1000.0, step=0.01, format="%.2f")
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

# STORICO FATTURE
elif st.session_state.pagina == "storico":
    st.header("📋 Storico Fatture")
    
    # Statistiche
    col1, col2, col3 = st.columns(3)
    col1.metric("Fatture Attive", len(st.session_state.dati_fatture["Attiva"]))
    col2.metric("Fatture Passive", len(st.session_state.dati_fatture["Passiva"]))
    col3.metric("Totale Attive", 
               f"€ {sum(f.get('totale', 0) for f in st.session_state.dati_fatture['Attiva']):.2f}")
    
    # Tabs per tipo
    tab1, tab2 = st.tabs(["Fatturazione Attiva", "Fatturazione Passiva"])
    
    with tab1:
        if st.session_state.dati_fatture["Attiva"]:
            df_attive = pd.DataFrame(st.session_state.dati_fatture["Attiva"])
            st.dataframe(df_attive, use_container_width=True)
        else:
            st.info("Nessuna fattura attiva registrata")
    
    with tab2:
        if st.session_state.dati_fatture["Passiva"]:
            df_passive = pd.DataFrame(st.session_state.dati_fatture["Passiva"])
            st.dataframe(df_passive, use_container_width=True)
        else:
            st.info("Nessuna fattura passiva registrata")
