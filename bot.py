import pdfplumber
import os
import re
from playwright.sync_api import sync_playwright

def estrai_dati_pdf(percorso_pdf):
    dati_partite = []
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            # Legge solo la prima pagina
            text = pdf.pages[0].extract_text()
            if not text: return "Circolo non trovato", []
            
            # Estrai Nome Circolo (solitamente riga 2)
            righe = text.split('\n')
            nome_circolo = righe[1].strip() if len(righe) > 1 else "Circolo sconosciuto"
            
            # Regex per estrarre: Orario, Gioc1, Gioc2
            # Pattern adattato per: "Inizio ore: 18:00" poi "Gioc1", "vs", "Gioc2"
            matches = re.findall(r"Inizio ore: (\d{2}:\d{2}).*?\n(.*?)\nvs\n(.*?)\n", text)
            for orario, g1, g2 in matches:
                dati_partite.append(f"{g1.strip()}; {g2.strip()}; {orario}")
    except:
        return "Errore lettura PDF", []
    return nome_circolo, dati_partite

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Context per evitare popup o blocchi
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        # URL di partenza (La pagina dove vedi la lista tornei)
        page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # 1. Trova tutti i link dei tornei
        # Assicurati che i link inizino con /Tornei/Dettaglio-Competizione
        elementi = page.query_selector_all("a[href*='Dettaglio-Competizione']")
        lista_url = list(set([el.get_attribute("href") for el in elementi]))
        
        with open("Report_Partite.txt", "w", encoding="utf-8") as f:
            f.write(f"Report Generato il: {os.path.basename(__file__)}\n\n")
            
            for url_relativo in lista_url:
                url_completo = "https://www.fitp.it" + url_relativo
                try:
                    page.goto(url_completo, wait_until="networkidle")
                    
                    # 2. Gestione download PDF
                    with page.expect_download(timeout=15000) as download_info:
                        page.click("#btnOrderGameDownload")
                    download = download_info.value
                    download.save_as("temp.pdf")
                    
                    # 3. Estrai e Scrivi
                    circolo, partite = estrai_dati_pdf("temp.pdf")
                    f.write(f"\n--- {circolo} ---\n")
                    if partite:
                        for p in partite:
                            f.write(f"{p}\n")
                    else:
                        f.write("Nessuna partita trovata nel PDF.\n")
                        
                    if os.path.exists("temp.pdf"): os.remove("temp.pdf")
                except:
                    continue 
        
        browser.close()

if __name__ == "__main__":
    run()
