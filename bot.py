import os
import pdfplumber
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

def estrai_partite_con_filtro(percorso_pdf):
    partite_valide = []
    # Generiamo le date per il filtro (formato gg/mm/aaaa)
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            testo_intero = page.extract_text()
            
            # Verifichiamo se nel PDF è presente la data di oggi o domani
            data_trovata = None
            if oggi in testo_intero: data_trovata = oggi
            elif domani in testo_intero: data_trovata = domani
            
            if not data_trovata: 
                return [] # Se non è oggi o domani, ignoriamo questo file

            # Estrazione tabelle dal PDF
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
                                    # Estrae l'orario dalla riga (es. "18:00")
                                    orario = r.replace("Inizio ore:", "").strip()
                                elif "vs" not in r.lower() and len(r) > 4:
                                    giocatori.append(r.strip())
                            
                            # Se abbiamo trovato l'orario e almeno due giocatori, salviamo
                            if len(giocatori) >= 2 and orario:
                                # Formato richiesto: Data; G1; G2; Orario
                                partite_valide.append(f"{data_trovata}; {giocatori[0]}; {giocatori[1]}; {orario}")
    except Exception as e:
        print(f"Errore durante l'estrazione: {e}")
        
    return partite_valide

def scarica_e_elabora(context, categoria_id, nome_file):
    page = context.new_page()
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
    
    try:
        # Filtro stato "In corso"
        page.select_option("#select_status", label="In corso")
        # Clic categoria
        page.click(f'a[data-id="{categoria_id}"]')
        page.wait_for_load_state("networkidle")
        
        # LOGICA PAGINAZIONE: Clicca finché il bottone esiste
        while True:
            bottone = page.locator("#btn-loadMore")
            # Controlla se il bottone esiste ed è visibile
            if bottone.is_visible():
                bottone.click()
                # Attesa dinamica per caricamento nuovi elementi
                page.wait_for_timeout(2500) 
            else:
                # Il bottone non è più visibile, usciamo dal ciclo
                break
                
    except Exception as e:
        print(f"Errore durante la navigazione: {e}")

    # Estrazione link tornei
    tornei = page.query_selector_all("a[href*='Dettaglio-Competizione']")
    urls = list(set([t.get_attribute("href") for t in tornei]))
    page.close()
    
    # Scrittura file
    with open(nome_file, "w", encoding="utf-8") as f:
        for url in urls:
            full_url = "https://www.fitp.it" + url
            p = context.new_page()
            try:
                p.goto(full_url, wait_until="domcontentloaded", timeout=20000)
                
                # Download diretto (senza passare per "Dettagli")
                if p.locator("#btnOrderGameDownload").is_visible():
                    with p.expect_download(timeout=15000) as download_info:
                        p.click("#btnOrderGameDownload")
                    download = download_info.value
                    download.save_as("temp.pdf")
                    
                    # Estrazione e scrittura dati
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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        
        # Esecuzione per entrambe le categorie
        scarica_e_elabora(context, "t_giovanili", "Giovanili_Partite.txt")
        scarica_e_elabora(context, "t_affiliati", "Open_Partite.txt")
        
        browser.close()

if __name__ == "__main__":
    run()
