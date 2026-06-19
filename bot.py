import os
import pdfplumber
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

def estrai_dati_da_pdf(percorso_pdf):
    # Funzione di estrazione invariata
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
    
    # --- FASE 1: CARICAMENTO TOTALE ---
    print(f"Caricamento totale lista per {categoria_id}...")
    while True:
        bottone = page.locator("#btn-loadMore")
        if bottone.is_visible():
            bottone.scroll_into_view_if_needed()
            bottone.click(force=True)
            page.wait_for_timeout(2000) # Aspetta che si carichino i nuovi elementi
        else:
            print("Lista caricata completamente.")
            break
            
    # --- FASE 2: RACCOLTA LINK ---
    # Una volta caricato tutto, prendiamo TUTTI i link in una lista statica
    elementi = page.locator("a[href*='Dettaglio-Competizione']").all()
    urls = [el.get_attribute("href") for el in elementi]
    print(f"Trovati {len(urls)} tornei totali. Inizio processamento...")
    page.close() # Chiudiamo la pagina di ricerca principale per non appesantire
    
    # --- FASE 3: ELABORAZIONE SEQUENZIALE ---
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(f"Report: {datetime.now().strftime('%d/%m/%Y')}\n")
        
        for url in urls:
            full_url = "https://www.fitp.it" + url
            # Apriamo una NUOVA pagina per ogni torneo (come richiesto)
            p = context.new_page()
            try:
                p.goto(full_url, wait_until="domcontentloaded", timeout=30000)
                
                # Cerchiamo il pulsante download
                if p.locator("#btnOrderGameDownload").is_visible():
                    with p.expect_download(timeout=10000) as download_info:
                        p.click("#btnOrderGameDownload")
                    download = download_info.value
                    download.save_as("temp.pdf")
                    
                    # Estrazione e scrittura
                    nome, partite = estrai_dati_da_pdf("temp.pdf")
                    if nome and partite:
                        f.write(f"\n>> {nome}\n")
                        for p_data in partite:
                            f.write(f"{p_data}\n")
                    
                    if os.path.exists("temp.pdf"): os.remove("temp.pdf")
            except Exception as e:
                print(f"Errore su {url}: {e}")
            finally:
                p.close() # Chiudiamo la scheda e passiamo alla prossima

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        # Eseguiamo prima giovanili, poi open
        scarica_e_elabora(context, "t_giovanili", "Giovanili_Partite.txt")
        scarica_e_elabora(context, "t_affiliati", "Open_Partite.txt")
        browser.close()

if __name__ == "__main__":
    run()
