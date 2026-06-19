import pdfplumber
import os
import re
from playwright.sync_api import sync_playwright

# --- Funzione per leggere il PDF ---
def estrai_dati_pdf(percorso_pdf):
    dati_partite = []
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            text = pdf.pages[0].extract_text()
            if not text: return "Circolo non trovato", []
            
            # Estrai Nome Circolo (riga 2)
            righe = text.split('\n')
            nome_circolo = righe[1] if len(righe) > 1 else "Circolo sconosciuto"
            
            # Regex per estrarre: Orario, Gioc1, Gioc2
            matches = re.findall(r"Inizio ore: (\d{2}:\d{2}).*?\n(.*?)\nvs\n(.*?)\n", text)
            for orario, g1, g2 in matches:
                dati_partite.append(f"{g1.strip()}; {g2.strip()}; {orario}")
    except:
        return "Errore lettura", []
    return nome_circolo, dati_partite

# --- Processo Principale ---
def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("URL_DEL_SITO_FITP_DA_DOVE_INIZIARE") # <--- INSERISCI QUI IL LINK PAGINA TORNEI
        
        # 1. Trova tutti i link dei tornei
        elementi = page.query_selector_all("a[href*='Dettaglio-Competizione']")
        lista_url = list(set([el.get_attribute("href") for el in elementi])) # Rimuove duplicati
        
        with open("Report_Partite.txt", "w", encoding="utf-8") as f:
            for url_relativo in lista_url:
                # Crea URL completo
                url_completo = "https://www.fitp.it" + url_relativo if url_relativo.startswith("/") else url_relativo
                
                try:
                    page.goto(url_completo, wait_until="networkidle")
                    
                    # 2. Scarica PDF
                    with page.expect_download(timeout=10000) as download_info:
                        page.click("#btnOrderGameDownload")
                    download = download_info.value
                    download.save_as("temp.pdf")
                    
                    # 3. Estrai e Scrivi
                    circolo, partite = estrai_dati_pdf("temp.pdf")
                    f.write(f"\n--- {circolo} ---\n")
                    for p in partite:
                        f.write(f"{p}\n")
                        
                    os.remove("temp.pdf") # Pulizia
                except:
                    continue # Se un torneo non ha il PDF, passa al prossimo
        
        browser.close()

if __name__ == "__main__":
    run()
