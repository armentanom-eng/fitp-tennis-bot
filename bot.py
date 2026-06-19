import os
import pdfplumber
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

def estrai_partite_pulite(percorso_pdf):
    partite_trovate = []
    # Creiamo i formati data per il confronto
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            testo = page.extract_text()
            
            # Determiniamo quale data usare
            data_valida = None
            if oggi in testo: data_valida = oggi
            elif domani in testo: data_valida = domani
            
            if not data_valida: return []

            # Analisi della tabella
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
                            
                            # Formato: Data; G1; G2; Orario
                            if len(giocatori) >= 2 and orario:
                                partite_trovate.append(f"{data_valida}; {giocatori[0]}; {giocatori[1]}; {orario}")
    except: pass
    return partite_trovate

def scarica_e_elabora(context, categoria_id, nome_file):
    page = context.new_page()
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
    
    # Selezione Categoria
    try:
        page.select_option("#select_status", label="In corso")
        page.click(f'a[data-id="{categoria_id}"]')
        page.wait_for_load_state("networkidle")
    except: pass
    
    # --- PAGINAZIONE: Clicca finché il bottone "Carica altri tornei" esiste ---
    while page.locator("#btn-loadMore").is_visible():
        page.click("#btn-loadMore")
        page.wait_for_timeout(2000) # Attende che i nuovi tornei vengano caricati
    
    # Raccolta di tutti i link dei tornei
    tornei = page.query_selector_all("a[href*='Dettaglio-Competizione']")
    urls = list(set([t.get_attribute("href") for t in tornei]))
    page.close()
    
    # Scrittura file
    with open(nome_file, "w", encoding="utf-8") as f:
        for url in urls:
            full_url = "https://www.fitp.it" + url
            p = context.new_page()
            try:
                p.goto(full_url, wait_until="domcontentloaded", timeout=15000)
                # Clicca direttamente il download senza cercare "Dettagli"
                if p.locator("#btnOrderGameDownload").is_visible():
                    with p.expect_download(timeout=10000) as dl:
                        p.click("#btnOrderGameDownload")
                    dl.value.save_as("temp.pdf")
                    
                    partite = estrai_partite_pulite("temp.pdf")
                    for p_data in partite:
                        f.write(f"{p_data}\n")
                    
                    if os.path.exists("temp.pdf"): os.remove("temp.pdf")
            except: pass
            finally: p.close()

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        # Elabora le due categorie
        scarica_e_elabora(context, "t_giovanili", "Giovanili_Partite.txt")
        scarica_e_elabora(context, "t_affiliati", "Open_Partite.txt")
        browser.close()

if __name__ == "__main__":
    run()
