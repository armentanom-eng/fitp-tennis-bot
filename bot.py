import os
import pdfplumber
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

def estrai_partite_pulite(percorso_pdf):
    partite_trovate = []
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            # Usiamo extract_tables per essere precisi con la griglia del PDF
            tabelle = page.extract_tables()
            
            for table in tabelle:
                for row in table:
                    for cella in row:
                        if cella and "Inizio ore:" in cella:
                            # Pulizia del testo nella cella
                            righe = cella.split('\n')
                            orario = ""
                            giocatori = []
                            
                            for r in righe:
                                if "Inizio ore:" in r:
                                    # Estrae solo l'orario (es. "18:00")
                                    orario = r.replace("Inizio ore:", "").strip()
                                elif "vs" not in r.lower() and len(r) > 4:
                                    giocatori.append(r.strip())
                            
                            # Se abbiamo trovato l'orario e almeno due giocatori, salviamo
                            if len(giocatori) >= 2 and orario:
                                # Formato richiesto: G1; G2; Orario
                                partite_trovate.append(f"{giocatori[0]}; {giocatori[1]}; {orario}")
    except Exception as e:
        print(f"Errore durante l'estrazione del PDF: {e}")
        
    return partite_trovate

def scarica_e_elabora(context, categoria_id, nome_file):
    page = context.new_page()
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
    
    try:
        page.select_option("#select_status", label="In corso")
        page.click(f'a[data-id="{categoria_id}"]')
        page.wait_for_load_state("networkidle")
        
        # --- LOGICA PAGINAZIONE ---
        # Clicca il pulsante finché esiste
        while True:
            bottone = page.locator("#btn-loadMore")
            if bottone.is_visible():
                bottone.click()
                page.wait_for_timeout(2000) # Attesa per caricamento nuovi elementi
            else:
                break
        # --------------------------
        
    except Exception as e:
        print(f"Errore navigazione: {e}")

    # Estrazione link tornei
    tornei = page.query_selector_all("a[href*='Dettaglio-Competizione']")
    urls = list(set([t.get_attribute("href") for t in tornei]))
    page.close()
    
    # Scrittura file pulito
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(f"Report Aggiornato: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
        
        for url in urls:
            full_url = "https://www.fitp.it" + url
            p = context.new_page()
            try:
                p.goto(full_url, wait_until="domcontentloaded", timeout=15000)
                if p.locator("#btnOrderGameDownload").is_visible():
                    with p.expect_download(timeout=10000) as download_info:
                        p.click("#btnOrderGameDownload")
                    download = download_info.value
                    download.save_as("temp.pdf")
                    
                    partite = estrai_partite_pulite("temp.pdf")
                    if partite:
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
