import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import json
import os

class FatturazioneApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestione Fatturazione Attiva/Passiva")
        self.root.geometry("600x500")
        self.dati_fatture = self.carica_dati()
        
        # Schermata iniziale
        self.setup_schermata_iniziale()
    
    def setup_schermata_iniziale(self):
        # Pulisci finestra
        for widget in self.root.winfo_children():
            widget.destroy()
        
        title = tk.Label(self.root, text="Scegli il tipo di fatturazione", font=("Arial", 16, "bold"))
        title.pack(pady=50)
        
        btn_attiva = tk.Button(self.root, text="FATTURAZIONE ATTIVA\n(Fatture emesse ai clienti)", 
                               font=("Arial", 12), bg="#4CAF50", fg="white", height=3, width=30,
                               command=self.apri_fatturazione_attiva)
        btn_attiva.pack(pady=20)
        
        btn_passiva = tk.Button(self.root, text="FATTURAZIONE PASSIVA\n(Fatture ricevute dai fornitori)", 
                                font=("Arial", 12), bg="#2196F3", fg="white", height=3, width=30,
                                command=self.apri_fatturazione_passiva)
        btn_passiva.pack(pady=20)
        
        btn_esci = tk.Button(self.root, text="Esci", font=("Arial", 12), bg="#f44336", fg="white",
                             command=self.root.quit)
        btn_esci.pack(pady=20)
    
    def apri_fatturazione_attiva(self):
        self.mostra_form("Attiva")
    
    def apri_fatturazione_passiva(self):
        self.mostra_form("Passiva")
    
    def mostra_form(self, tipo):
        # Pulisci finestra
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Titolo
        titolo = tk.Label(self.root, text=f"Fatturazione {tipo}", font=("Arial", 16, "bold"))
        titolo.pack(pady=10)
        
        # Frame per i campi
        frame = ttk.Frame(self.root)
        frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        # Campi comuni
        ttk.Label(frame, text="Data (GG/MM/AAAA):").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_data = ttk.Entry(frame)
        self.entry_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.entry_data.grid(row=0, column=1, pady=5, sticky="ew")
        
        ttk.Label(frame, text="Numero Protocollo:").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_numero = ttk.Entry(frame)
        self.entry_numero.insert(0, "2026/1")
        self.entry_numero.grid(row=1, column=1, pady=5, sticky="ew")
        
        ttk.Label(frame, text="Nome Cliente/Fornitore:").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_nome = ttk.Entry(frame)
        self.entry_nome.insert(0, "Mario Rossi Srl" if tipo == "Attiva" else "Fornitore XYZ")
        self.entry_nome.grid(row=2, column=1, pady=5, sticky="ew")
        
        ttk.Label(frame, text="P.IVA / CF:").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_piva = ttk.Entry(frame)
        self.entry_piva.insert(0, "IT12345678901")
        self.entry_piva.grid(row=3, column=1, pady=5, sticky="ew")
        
        ttk.Label(frame, text="Imponibile (€):").grid(row=4, column=0, sticky="w", pady=5)
        self.entry_imponibile = ttk.Entry(frame)
        self.entry_imponibile.insert(0, "1000")
        self.entry_imponibile.grid(row=4, column=1, pady=5, sticky="ew")
        self.entry_imponibile.bind("<KeyRelease>", self.calcola_totali)
        
        ttk.Label(frame, text="Aliquota IVA (%):").grid(row=5, column=0, sticky="w", pady=5)
        self.entry_iva = ttk.Entry(frame)
        self.entry_iva.insert(0, "22")
        self.entry_iva.grid(row=5, column=1, pady=5, sticky="ew")
        self.entry_iva.bind("<KeyRelease>", self.calcola_totali)
        
        # Totali
        self.label_totali = ttk.Label(frame, text="Totale: € 0,00", font=("Arial", 12, "bold"))
        self.label_totali.grid(row=6, column=0, columnspan=2, pady=10)
        
        ttk.Label(frame, text="Modalità Pagamento:").grid(row=7, column=0, sticky="w", pady=5)
        self.entry_pagamento = ttk.Entry(frame)
        self.entry_pagamento.insert(0, "Bonifico 30gg")
        self.entry_pagamento.grid(row=7, column=1, pady=5, sticky="ew")
        
        # Note
        ttk.Label(frame, text="Note:").grid(row=8, column=0, sticky="w", pady=5)
        self.text_note = tk.Text(frame, height=3, width=40)
        self.text_note.grid(row=8, column=1, pady=5, sticky="ew")
        
        frame.grid_columnconfigure(1, weight=1)
        
        # Pulsanti
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="Salva Fattura", command=lambda: self.salva_fattura(tipo)).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Genera PDF", command=lambda: self.genera_pdf(tipo)).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Indietro", command=self.setup_schermata_iniziale).pack(side="left", padx=10)
        
        self.calcola_totali()
    
    def calcola_totali(self, event=None):
        try:
            imponibile = float(self.entry_imponibile.get() or 0)
            iva_perc = float(self.entry_iva.get() or 0) / 100
            iva = imponibile * iva_perc
            totale = imponibile + iva
            self.label_totali.config(text=f"IVA: € {iva:.2f} | Totale: € {totale:.2f}")
        except ValueError:
            pass
    
    def salva_fattura(self, tipo):
        fattura = {
            "tipo": tipo,
            "data": self.entry_data.get(),
            "numero": self.entry_numero.get(),
            "cliente_fornitore": self.entry_nome.get(),
            "piva": self.entry_piva.get(),
            "imponibile": self.entry_imponibile.get(),
            "iva_perc": self.entry_iva.get(),
            "totale": self.label_totali.cget("text").split("Totale: € ")[1],
            "pagamento": self.entry_pagamento.get(),
            "note": self.text_note.get("1.0", tk.END).strip(),
            "timestamp": datetime.now().isoformat()
        }
        self.dati_fatture[tipo].append(fattura)
        self.salva_dati()
        messagebox.showinfo("Successo", "Fattura salvata correttamente!")
    
    def carica_dati(self):
        if os.path.exists("fatture.json"):
            with open("fatture.json", "r") as f:
                return json.load(f)
        return {"Attiva": [], "Passiva": []}
    
    def salva_dati(self):
        with open("fatture.json", "w") as f:
            json.dump(self.dati_fatture, f, indent=4)
    
    def genera_pdf(self, tipo):
        messagebox.showinfo("PDF", f"PDF generato per {tipo}! (Implementa reportlab per export reale)")

if __name__ == "__main__":
    root = tk.Tk()
    app = FatturazioneApp(root)
    root.mainloop()
