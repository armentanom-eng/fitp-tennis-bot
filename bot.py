import pdfplumber
import os
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # INSERISCI QUI UN URL DI UN TORNEO REALE (Prendilo dal browser)
        url_test = "https://www.fitp.it/Tornei/Dettaglio-Competizione.html?competitionId=..." 
        print(f"Sto navigando su: {url_test}")
        
        page.goto(url_test, wait_until="networkidle")
        
        # Vediamo cosa c'è nella pagina
        print("Pagina caricata. Cerco il bottone...")
        
        try:
            with page.expect_download(timeout=10000) as download_info:
                # Se questo fallisce, l'errore apparirà nei log
                page.click("#btnOrderGameDownload")
            
            download = download_info.value
            download.save_as("test_debug.pdf")
            print("Download completato! File salvato.")
            
            with pdfplumber.open("test_debug.pdf") as pdf:
                print("PDF aperto correttamente.")
                print("Testo trovato:", pdf.pages[0].extract_text()[:200])
        except Exception as e:
            print(f"ERRORE CRITICO: {e}")

if __name__ == "__main__":
    run()
