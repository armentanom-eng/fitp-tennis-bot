import os
import pdfplumber
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

def estrai_partite_con_filtro(percorso_pdf):
    partite_valide = []
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            testo_intero = page.extract_text()
            data_trovata = None
            if oggi in testo_intero: data_trovata = oggi
            elif domani in testo_intero: data_trovata = domani
            
            if not data_trovata: return []

            tabelle = page.extract_tables()
            for table in tabelle:
                for row in table:
                    for cella in row:
                        if cella and "Inizio ore:" in cella:
                            righe = cella.split('\n')
                            orario = ""
                            giocatori = []
                            for r in righe:
                                if "Inizio ore:" in r:
                                    orario = r.replace("Inizio ore:", "").strip()
                                elif "vs" not in r.lower() and len(r) > 4:
                                    giocatori.append(r.strip())
                            
                            if len(giocatori) >= 2 and orario:
                                partite_valide.append(f"{data_trovata}; {giocatori[0]}; {giocatori[1]}; {orario}")
    except: pass
    return partite_valide

def scarica_e_elabora(context, categoria_id, nome_file):
    page = context.new_page()
    # Usiamo 'domcontentloaded' che è molto più veloce e non si blocca sui caricamenti infiniti
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
    
    try:
        page.select_option("#select_status", label="In corso")
        page.click(f'a[data-id="{categoria_id}"]')
        # Aspettiamo che appaiano i risultati invece di aspettare la rete inattiva
        page.wait_for_timeout(5000) 
        
        # --- CARICAMENTO TOTALE ---
        while True:
            bottone = page.locator("#btn-loadMore")
            if bottone.is_visible():
                bottone.click()
                page.wait_for_timeout(3000) # Pausa di sicurezza
            else:
                break
    except: pass
    
    tornei_elements = page.query_selector_all("a[href*='Dettaglio-Competizione']")
    urls = list(set([t.get_attribute("href") for t in tornei_elements]))
    page.close()
    
    with open(nome_file, "w", encoding="utf-8") as f:
        for url in urls:
            full_url = "https://www.fitp.it" + url
            p = context.new_page()
            try:
                # Anche qui, carichiamo in modo più flessibile
                p.goto(full_url, wait_until="domcontentloaded", timeout=30000)
                
                # Se il tasto download appare, scarichiamo
                if p.locator("#btnOrderGameDownload").is_visible():
                    with p.expect_download(timeout=15000) as download_info:
                        p.click("#btnOrderGameDownload")
                    download = download_info.value
                    download.save_as("temp.pdf")
                    
                    partite = estrai_partite_con_filtro("temp.pdf")
                    for p_data in partite:
                        f.write(f"{p_data}\n")
                    
                    if os.path.exists("temp.pdf"): os.remove("temp.pdf")
            except: pass
            finally: p.close()

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        
        scarica_e_elabora(context, "t_giovanili", "Giovanili_Partite.txt")
        scarica_e_elabora(context, "t_affiliati", "Open_Partite.txt")
        
        browser.close()

if __name__ == "__main__":
    run()
