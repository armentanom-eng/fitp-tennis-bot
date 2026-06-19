import os
import pdfplumber
from playwright.sync_api import sync_playwright
from datetime import datetime

def estrai_partite_robusto(percorso_pdf):
    partite_trovate = []
    nome_circolo = "Circolo Non Trovato"
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            page = pdf.pages[0]
            testo = page.extract_text()
            if not testo: return nome_circolo, []
            
            linee = testo.split('\n')
            # La prima riga è solitamente il nome del circolo
            nome_circolo = linee[0].strip()
            
            # Scorriamo le righe cercando il pattern
            for i in range(len(linee)):
                if "Inizio ore:" in linee[i]:
                    orario = linee[i].replace("Inizio ore:", "").strip()
                    
                    # Proviamo a prendere le righe successive (giocatori)
                    # Solitamente: riga(i+1) è Categoria, riga(i+2) è Gioc1, riga(i+3) è vs, riga(i+4) è Gioc2
                    try:
                        # Cerchiamo di trovare i giocatori ignorando la categoria
                        giocatore1 = linee[i+2].strip()
                        # La riga i+3 contiene "vs" o un separatore
                        giocatore2 = linee[i+4].strip()
                        
                        # Pulizia: scartiamo righe che contengono 'vs' o sono troppo corte
                        if "vs" not in giocatore1.lower() and len(giocatore1) > 4:
                             partite_trovate.append(f"{giocatore1}; {giocatore2}; {orario}")
                    except:
                        continue
                        
    except Exception as e:
        print(f"Errore lettura: {e}")
        
    return nome_circolo, partite_trovate

def scarica_e_elabora(context, categoria_id, nome_file):
    page = context.new_page()
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
    
    try:
        page.select_option("#select_status", label="In corso")
        page.click(f'a[data-id="{categoria_id}"]')
        page.wait_for_load_state("networkidle")
    except: pass

    urls = [t.get_attribute("href") for t in page.query_selector_all("a[href*='Dettaglio-Competizione']")]
    page.close()
    
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(f"Report: {datetime.now().strftime('%d/%m/%Y')}\n\n")
        for url in list(set(urls)):
            full_url = "https://www.fitp.it" + url
            p = context.new_page()
            try:
                p.goto(full_url, wait_until="networkidle", timeout=20000)
                if p.locator("#btnOrderGameDownload").is_visible():
                    with p.expect_download() as download_info:
                        p.click("#btnOrderGameDownload")
                    download = download_info.value
                    download.save_as("temp.pdf")
                    
                    nome, partite = estrai_partite_robusto("temp.pdf")
                    if partite:
                        f.write(f"\n>> {nome}\n")
                        for p_data in partite:
                            f.write(f"{p_data}\n")
                    if os.path.exists("temp.pdf"): os.remove("temp.pdf")
            except Exception as e: print(f"Errore: {e}")
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
