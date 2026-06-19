import os
import pdfplumber
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import time

def estrai_partite_con_filtro(percorso_pdf):
    partite_valide = []
    # Data oggi e domani per il filtro
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            testo_intero = page.extract_text()
            
            # Controllo se nel PDF c'è la data di oggi o domani
            data_trovata = None
            if oggi in testo_intero: data_trovata = oggi
            elif domani in testo_intero: data_trovata = domani
            
            if not data_trovata: 
                return [] 

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
                                partite_valide.append(f"{data_trovata}; {giocatori[0]}; {giocatori[1]}; {orario}")
    except Exception as e:
        print(f"Errore estrazione PDF: {e}")
        
    return partite_valide

def scarica_e_elabora(context, categoria_id, nome_file):
    page = context.new_page()
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
    
    # 1. Seleziona Categoria
    page.select_option("#select_status", label="In corso")
    page.click(f'a[data-id="{categoria_id}"]')
    page.wait_for_load_state("networkidle")
    
    # 2. CARICAMENTO TOTALE: Clicca il bottone finché esiste
    print(f"Caricamento tornei per {categoria_id}...")
    while True:
        bottone = page.locator("#btn-loadMore")
        if bottone.is_visible():
            bottone.click()
            # Attesa più lunga per garantire il caricamento dei nuovi elementi
            page.wait_for_timeout(3000) 
        else:
            print("Tutti i tornei caricati.")
            break
    
    # 3. ESTRAZIONE LINK (dopo che tutto è stato caricato)
    tornei_elements = page.query_selector_all("a[href*='Dettaglio-Competizione']")
    urls = []
    for t in tornei_elements:
        href = t.get_attribute("href")
        if href and href not in urls:
            urls.append(href)
    
    print(f"Trovati {len(urls)} tornei da processare.")
    page.close()
    
    # 4. Elaborazione sequenziale dei link
    with open(nome_file, "w", encoding="utf-8") as f:
        for url in urls:
            full_url = "https://www.fitp.it" + url
            p = context.new_page()
            try:
                p.goto(full_url, wait_until="domcontentloaded", timeout=20000)
                
                if p.locator("#btnOrderGameDownload").is_visible():
                    with p.expect_download(timeout=15000) as download_info:
                        p.click("#btnOrderGameDownload")
                    download = download_info.value
                    download.save_as("temp.pdf")
                    
                    # Estrai dati dal PDF appena scaricato
                    partite = estrai_partite_con_filtro("temp.pdf")
                    for p_data in partite:
                        f.write(f"{p_data}\n")
                    
                    if os.path.exists("temp.pdf"): os.remove("temp.pdf")
            except Exception as e:
                print(f"Errore nel processare {full_url}: {e}")
            finally: 
                p.close()

def run():
    with sync_playwright() as p:
        # Uso 'headless=True' per GitHub Actions
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        
        scarica_e_elabora(context, "t_giovanili", "Giovanili_Partite.txt")
        scarica_e_elabora(context, "t_affiliati", "Open_Partite.txt")
        
        browser.close()

if __name__ == "__main__":
    run()
