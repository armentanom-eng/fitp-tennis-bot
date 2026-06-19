import time
from playwright.sync_api import sync_playwright

def scarica_dati(page, categoria_id, nome_file):
    print(f"--- Inizio elaborazione: {nome_file} ---")
    
    # 1. Vai alla pagina ricerca
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
    
    # 2. Imposta filtro "In corso" (se il selettore esiste)
    try:
        page.select_option("#select_status", label="In corso")
        page.wait_for_timeout(2000) # Attesa per caricamento dati dopo filtro
    except:
        print("Filtro 'In corso' non trovato, procedo con default.")

    # 3. Clicca la categoria (Giovanili o Open)
    try:
        page.click(f'a[data-id="{categoria_id}"]')
        page.wait_for_timeout(3000) # Attesa fondamentale
    except Exception as e:
        print(f"Errore cambio categoria: {e}")
        return

    # 4. Loop per cliccare "Carica altri" finché esiste
    print("Inizio caricamento completo lista...")
    while True:
        try:
            btn_more = page.locator("#btn-loadMore")
            if btn_more.is_visible():
                btn_more.click()
                page.wait_for_timeout(2000) # Aspetta che carichi altri elementi
                print("Caricati altri tornei...")
            else:
                print("Tutti i tornei caricati.")
                break
        except:
            break

    # 5. Estrai i link dei dettagli
    # Cerchiamo tutti i link che portano ai dettagli torneo
    tornei = page.query_selector_all("a[href*='Dettaglio-Competizione']")
    urls = [t.get_attribute("href") for t in tornei]
    
    print(f"Trovati {len(urls)} tornei.")

    # 6. Analizza i dettagli per ogni torneo
    risultati = []
    for url in urls:
        # Costruiamo l'URL completo se necessario
        full_url = "https://www.fitp.it" + url if url.startswith('/') else url
        
        # Apriamo una nuova pagina per il dettaglio
        new_page = page.context.new_page()
        try:
            new_page.goto(full_url, wait_until="networkidle", timeout=30000)
            
            # Verifica presenza bottone download
            if new_page.locator("#btnOrderGameDownload").is_visible():
                risultati.append(f"TORNEO: {new_page.title()} | DOWNLOAD: DISPONIBILE | URL: {full_url}")
            else:
                risultati.append(f"TORNEO: {new_page.title()} | DOWNLOAD: NON TROVATO | URL: {full_url}")
        except Exception as e:
            print(f"Errore su torneo {full_url}: {e}")
        finally:
            new_page.close()

    # 7. Scrittura file
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(f"Report {nome_file} - {time.ctime()}\n\n")
        f.write("\n".join(risultati))
    print(f"--- Salvato {nome_file} ---")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Esegui per Giovanili (t_giovanili)
        scarica_dati(page, "t_giovanili", "Giovanili_Partite.txt")
        
        # Esegui per Open (t_open - ipotizzando l'ID, controlla se è t_open o simile nel tuo ispezione)
        # Nota: controlla il data-id dell'elemento Open nel tuo browser e cambialo qui se diverso
        scarica_dati(page, "t_open", "Open_Partite.txt") 
        
        browser.close()

if __name__ == "__main__":
    run()
