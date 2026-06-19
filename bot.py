import time
import os
import pdfplumber
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

def block_resources(route):
    if route.request.resource_type in ["image", "font", "stylesheet", "media", "other"]:
        route.abort()
    else:
        route.continue_()

def estrai_dati_da_pdf(percorso_pdf):
    # Formato data da cercare (es: 19/06/2026)
    target_dates = [
        datetime.now().strftime("%d/%m/%Y"), 
        (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    ]
    
    nome_circolo = "Circolo Non Trovato"
    partite_trovate = []
    data_corrente = None

    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            # Estrai circolo dalla prima riga del testo
            testo = page.extract_text()
            if testo:
                nome_circolo = testo.split('\n')[0].strip()

            tabelle = page.extract_tables()
            for table in tabelle:
                for row in table:
                    # Verifica data nella riga
                    for cella in row:
                        if cella:
                            for d in target_dates:
                                if d in cella:
                                    data_corrente = d
                    
                    # Se la riga contiene dati partita e siamo nella data giusta
                    if data_corrente:
                        # Cerchiamo riga con "Inizio ore"
                        for cella in row:
                            if cella and "Inizio ore:" in cella:
                                righe = cella.split('\n')
                                orario = ""
                                giocatori = []
                                for r in righe:
                                    if "Inizio ore:" in r:
                                        orario = r.replace("Inizio ore:", "").strip()
                                    elif "vs" not in r.lower() and len(r) > 3:
                                        giocatori.append(r.strip())
                                
                                if len(giocatori) >= 2 and orario:
                                    partite_trovate.append(f"{giocatori[0]}; {giocatori[1]}; {orario}")
                                    
    except Exception as e:
        print(f"Errore PDF: {e}")
        
    return nome_circolo, partite_trovate

def scarica_dati(context, categoria_id, nome_file):
    page = context.new_page()
    page.route("**/*", block_resources)
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
    
    try:
        page.select_option("#select_status", label="In corso")
        page.click(f'a[data-id="{categoria_id}"]')
        page.wait_for_load_state("domcontentloaded")
    except: pass

    tornei = page.query_selector_all("a[href*='Dettaglio-Competizione']")
    urls = list(set([t.get_attribute("href") for t in tornei]))
    page.close()
    
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(f"Report Aggiornato: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
        
        for url in urls:
            full_url = "https://www.fitp.it" + url if url.startswith('/') else url
            p = context.new_page()
            p.route("**/*", block_resources)
            try:
                p.goto(full_url, wait_until="domcontentloaded", timeout=15000)
                if p.locator("#btnOrderGameDownload").is_visible(timeout=5000):
                    with p.expect_download(timeout=10000) as download_info:
                        p.click("#btnOrderGameDownload")
                    
                    download = download_info.value
                    download.save_as("temp.pdf")
                    
                    nome, partite = estrai_dati_da_pdf("temp.pdf")
                    if partite:
                        f.write(f"\n>> {nome}\n")
                        for p_data in partite:
                            f.write(f"{p_data}\n")
                    
                    if os.path.exists("temp.pdf"): os.remove("temp.pdf")
            except: pass
            finally: p.close()

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        scarica_dati(context, "t_giovanili", "Giovanili_Partite.txt")
        scarica_dati(context, "t_affiliati", "Open_Partite.txt")
        browser.close()

if __name__ == "__main__":
    run()
