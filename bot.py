import os
import pdfplumber
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

# Funzione di estrazione invariata (quella che ti piace)
def estrai_dati_da_pdf(percorso_pdf):
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    partite_trovate = []
    nome_circolo = "Circolo Non Trovato"
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            testo = page.extract_text()
            if not testo: return None, []
            
            # Filtro data
            if oggi not in testo and domani not in testo:
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
    
    # Setup iniziale categoria
    page.select_option("#select_status", label="In corso")
    page.click(f'a[data-id="{categoria_id}"]')
    page.wait_for_timeout(3000)
    
    # Set per tenere traccia dei tornei già elaborati
    processati = set()
    
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(f"Report: {datetime.now().strftime('%d/%m/%Y')}\n")
        
        while True:
            # 1. Trova tutti i link "Dettagli" attualmente presenti nella pagina
            links = page.query_selector_all("a[href*='Dettaglio-Competizione']")
            
            nuovi_tornei = []
            for link in links:
                url = link.get_attribute("href")
                if url not in processati:
                    nuovi_tornei.append(url)
                    processati.add(url)
            
            # 2. Elabora solo i NUOVI trovati in questo blocco
            for url in nuovi_tornei:
                full_url = "https://www.fitp.it" + url
                p = context.new_page() # Apriamo in una nuova scheda
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
                except Exception as e:
                    print(f"Errore su {url}: {e}")
                finally:
                    p.close() # Chiudiamo la scheda per tornare alla lista
            
            # 3. Clicca "Carica altri" e attendi il caricamento dei nuovi elementi
            bottone = page.locator("#btn-loadMore")
            if bottone.is_visible():
                bottone.click()
                page.wait_for_timeout(4000) # Attesa generosa per far caricare il nuovo blocco
            else:
                break # Non c'è più il bottone, abbiamo finito
    
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
