import os
import pdfplumber
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

def estrai_dati_da_pdf(percorso_pdf):
    # Logica di estrazione (rimane invariata)
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    partite_trovate = []
    nome_circolo = "Circolo Non Trovato"
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            testo = page.extract_text()
            if not testo or (oggi not in testo and domani not in testo):
                return None, []
            
            linee = testo.split('\n')
            nome_circolo = linee[0].strip()
            for i in range(len(linee)):
                if "Inizio ore:" in linee[i]:
                    orario = linee[i].replace("Inizio ore:", "").strip()
                    try:
                        giocatore1 = linee[i+2].strip()
                        giocatore2 = linee[i+4].strip()
                        if "vs" not in giocatore1.lower() and len(giocatore1) > 4:
                             partite_trovate.append(f"{giocatore1}; {giocatore2}; {orario}")
                    except: continue
    except: pass
    return nome_circolo, partite_trovate

def scarica_e_elabora(context, categoria_id, nome_file):
    page = context.new_page()
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
    
    page.select_option("#select_status", label="In corso")
    page.click(f'a[data-id="{categoria_id}"]')
    page.wait_for_timeout(3000)
    
    processati = set()  # Serve per tenere traccia di cosa abbiamo già fatto
    
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(f"Report: {datetime.now().strftime('%d/%m/%Y')}\n")
        
        while True:
            # 1. Trova tutti i link attualmente visibili
            elements = page.query_selector_all("a[href*='Dettaglio-Competizione']")
            nuovi_tornei = []
            
            for t in elements:
                url = t.get_attribute("href")
                if url and url not in processati:
                    nuovi_tornei.append(url)
                    processati.add(url)
            
            # 2. Processa solo i NUOVI trovati
            for url in nuovi_tornei:
                full_url = "https://www.fitp.it" + url
                # Apriamo in una nuova pagina per non perdere la lista principale
                p = context.new_page()
                try:
                    p.goto(full_url, wait_until="domcontentloaded", timeout=20000)
                    if p.locator("#btnOrderGameDownload").is_visible():
                        with p.expect_download(timeout=10000) as download_info:
                            p.click("#btnOrderGameDownload")
                        download = download_info.value
                        download.save_as("temp.pdf")
                        
                        nome, partite = estrai_dati_da_pdf("temp.pdf")
                        if nome and partite:
                            f.write(f"\n>> {nome}\n")
                            for p_data in partite:
                                f.write(f"{p_data}\n")
                        if os.path.exists("temp.pdf"): os.remove("temp.pdf")
                except: pass
                finally: p.close()
            
            # 3. Ora clicchiamo "Carica altri" per la prossima batch
            bottone = page.locator("#btn-loadMore")
            if bottone.is_visible():
                bottone.click()
                page.wait_for_timeout(3000) # Aspetta che si carichino i nuovi
            else:
                break # Non c'è più nulla da caricare, usciamo
    
    page.close()

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        scarica_e_elabora(context, "t_giovanili", "Giovanili_Partite.txt")
        scarica_e_elabora(context, "t_affiliati", "Open_Partite.txt")
        browser.close()

if __name__ == "__main__":
    run()
