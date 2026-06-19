import os
import shutil
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
import pdfplumber

# Configurazione
FILE_REPORT = "Report_Partite.txt"
URL_BASE = "https://www.fitp.it/Tornei/Ricerca-tornei"

def run():
    # Inizializza il file
    with open(FILE_REPORT, "w", encoding="utf-8") as f:
        f.write(f"--- BOLLETTINO AUTOMATICO {datetime.now().strftime('%d/%m/%Y')} ---\n\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL_BASE)
        
        # Esempio: Scegliamo di lavorare sulle date 'Oggi' e 'Domani'
        date_da_processare = [datetime.now(), datetime.now() + timedelta(days=1)]
        
        for data in date_da_processare:
            label = "OGGI" if data.date() == datetime.now().date() else "DOMANI"
            
            # Qui andrebbe la logica specifica per selezionare la data nel calendario del sito
            # Per ora, scriviamo nel file che stiamo iniziando l'elaborazione
            with open(FILE_REPORT, "a", encoding="utf-8") as f:
                f.write(f"\n### {label} ({data.strftime('%d/%m/%Y')})\n")
            
            # Qui il bot cercherebbe i PDF (usando la logica di download discussa)
            # Esempio fittizio di estrazione:
            # page.fill("input[type='date']", data.strftime("%Y-%m-%d"))
            # page.click("text='Scarica'")
            
            print(f"Processato: {label}")

        browser.close()

if __name__ == "__main__":
    run()
