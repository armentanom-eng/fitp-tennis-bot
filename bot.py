import os
import pdfplumber
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

def estrai_dati_da_pdf(percorso_pdf, data_target):
    """
    Estrae le partite dal PDF e le formatta per la scrittura.
    """
    partite_trovate = []
    nome_circolo = "Circolo Non Trovato"
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            if not pdf.pages: return None, []
            page = pdf.pages[0]
            testo = page.extract_text()
            if not testo: return None, []
            
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
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
    
    # Filtro iniziale
    page.select_option("#select_status", label="In corso")
    page.click(f'a[data-id="{categoria_id}"]')
    page.wait_for_timeout(3000)
    
    # --- FASE 1: CARICAMENTO TOTALE ---
    print(f"[{categoria_id}] Caricamento lista completa...")
    while True:
        bottone = page.locator("#btn-loadMore")
        if bottone.is_visible():
            bottone.scroll_into_view_if_needed()
            bottone.click(force=True)
            page.wait_for_timeout(3000) # Attesa necessaria per caricamento dati
        else:
            break
            
    # --- FASE 2: RACCOLTA URL ---
    elementi = page.locator("a[href*='Dettaglio-Competizione']").all()
    urls = []
    for el in elementi:
        url = el.get_attribute("href")
        if url and url not in urls:
            urls.append(url)
    
    print(f"[{categoria_id}] Trovati {len(urls)} tornei. Inizio elaborazione...")
    page.close() 
    
    # --- FASE 3: ELABORAZIONE E SCRITTURA (MODALITÀ APPEND) ---
    with open(nome_file, "a", encoding="utf-8") as f:
        f.write(f"\n\n--- INIZIO SESSIONE {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ---\n")
        
        for url in urls:
            full_url = "https://www.fitp.it" + url
            p = context.new_page()
            try:
                p.goto(full_url, wait_until="networkidle", timeout=60000)
                
                # Definiamo le date target
                oggi = datetime.now().strftime("%d/%m/%Y")
                domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
                date_da_processare = [oggi, domani]
                
                for data_target in date_da_processare:
                    try:
                        # 1. Selezioniamo la data dal menù (dropdown)
                        # Nota: Assicurati che il selettore "select" sia corretto per la tua pagina
                        if p.locator("select").count() > 0:
                            p.select_option("select", label=data_target)
                            p.wait_for_timeout(3000) # Attesa che la pagina ricarichi i dati per la data scelta
                            
                            # 2. Clicchiamo Scarica
                            bottone_scarica = p.locator("text=Scarica")
                            if bottone_scarica.is_visible():
                                with p.expect_download(timeout=15000) as download_info:
                                    bottone_scarica.click()
                                
                                download = download_info.value
                                temp_path = f"temp_{data_target.replace('/', '-')}.pdf"
                                download.save_as(temp_path)
                                
                                # 3. Estrazione e Scrittura in Append
                                nome, partite = estrai_dati_da_pdf(temp_path, data_target)
                                if nome and partite:
                                    f.write(f"\n>> {nome} (Data: {data_target})\n")
                                    for p_data in partite:
                                        f.write(f"{p_data}\n")
                                
                                if os.path.exists(temp_path): os.remove(temp_path)
                                
                    except Exception as e:
                        print(f"Data {data_target} non disponibile per {url}")
                        
            except Exception as e:
                print(f"Errore su {url}: {e}")
            finally:
                p.close()

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # Metti False se vuoi vedere cosa fa
        context = browser.new_context(accept_downloads=True)
        
        scarica_e_elabora(context, "t_giovanili", "Giovanili_Partite.txt")
        scarica_e_elabora(context, "t_affiliati", "Open_Partite.txt")
        
        browser.close()

if __name__ == "__main__":
    run()
