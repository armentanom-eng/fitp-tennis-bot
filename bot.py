import pdfplumber
import os
import re
from playwright.sync_api import sync_playwright

def estrai_dati_pdf(percorso_pdf):
    print(f"--- Lettura PDF: {percorso_pdf} ---")
    dati_partite = []
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            text = page.extract_text()
            print("Testo estratto dal PDF (prime 100 caratteri):")
            print(text[:100]) # Questo ti serve per vedere se legge davvero il PDF
            
            if not text: 
                print("PDF vuoto o illeggibile!")
                return "Circolo non trovato", []
            
            righe = text.split('\n')
            nome_circolo = righe[1].strip() if len(righe) > 1 else "Circolo sconosciuto"
            
            # Regex: cerchiamo in tutto il testo
            matches = re.findall(r"Inizio ore: (\d{2}:\d{2}).*?\n(.*?)\nvs\n(.*?)\n", text)
            print(f"Trovate {len(matches)} partite nel PDF.")
            
            for orario, g1, g2 in matches:
                dati_partite.append(f"{g1.strip()}; {g2.strip()}; {orario}")
    except Exception as e:
        print(f"Errore durante l'estrazione: {e}")
        return "Errore", []
    return nome_circolo, dati_partite

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        # URL
        target_url = "https://www.fitp.it/Tornei/Ricerca-tornei" # Verifica che sia questo l'URL corretto
        print(f"Navigazione su: {target_url}")
        page.goto(target_url, wait_until="networkidle")
        
        # 1. Trova link
        elementi = page.query_selector_all("a[href*='Dettaglio-Competizione']")
        lista_url = list(set([el.get_attribute("href") for el in elementi]))
        print(f"Trovati {len(lista_url)} tornei.")
        
        with open("Report_Partite.txt", "w", encoding="utf-8") as f:
            f.write(f"Report Generato il: {os.path.basename(__file__)}\n\n")
            
            for url_relativo in lista_url:
                url_completo = "https://www.fitp.it" + url_relativo
                print(f"--- Elaborazione: {url_completo} ---")
                
                page.goto(url_completo, wait_until="networkidle")
                
                # 2. Download
                # Se il click fallisce, vedrai l'errore nei log di GitHub!
                with page.expect_download(timeout=15000) as download_info:
                    page.click("#btnOrderGameDownload")
                download = download_info.value
                download.save_as("temp.pdf")
                
                # 3. Estrai
                circolo, partite = estrai_dati_pdf("temp.pdf")
                f.write(f"\n--- {circolo} ---\n")
                for p in partite:
                    f.write(f"{p}\n")
                    
                if os.path.exists("temp.pdf"): os.remove("temp.pdf")
        
        browser.close()

if __name__ == "__main__":
    run()
