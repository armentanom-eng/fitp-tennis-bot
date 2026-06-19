import time
from playwright.sync_api import sync_playwright

def scarica_dati(page, categoria_id, nome_file):
    print(f"--- Inizio elaborazione: {nome_file} ---")
    page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
    
    # 1. Filtro "In corso"
    try:
        page.select_option("#select_status", label="In corso")
        page.wait_for_timeout(3000) 
    except:
        pass

    # 2. Clicca categoria
    try:
        page.click(f'a[data-id="{categoria_id}"]')
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"Errore categoria {categoria_id}: {e}")
        return

    # 3. Caricamento totale
    print("Caricamento lista completa...")
    while True:
        try:
            btn = page.locator("#btn-loadMore")
            if btn.is_visible(timeout=5000):
                btn.click()
                page.wait_for_timeout(2000)
            else:
                break
        except:
            break

    # 4. Estrazione
    tornei = page.query_selector_all("a[href*='Dettaglio-Competizione']")
    urls = [t.get_attribute("href") for t in tornei]
    
    risultati = []
    for url in urls:
        full_url = "https://www.fitp.it" + url if url.startswith('/') else url
        new_page = page.context.new_page()
        try:
            new_page.goto(full_url, wait_until="networkidle", timeout=30000)
            if new_page.locator("#btnOrderGameDownload").is_visible():
                risultati.append(f"TORNEO: {new_page.title()} | DOWNLOAD: OK | URL: {full_url}")
            else:
                risultati.append(f"TORNEO: {new_page.title()} | DOWNLOAD: NO | URL: {full_url}")
        except:
            risultati.append(f"ERRORE: {full_url}")
        finally:
            new_page.close()

    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(f"Report {nome_file} - {time.ctime()}\n\n")
        f.write("\n".join(risultati))

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Esegui per Giovanili e Open
        scarica_dati(page, "t_giovanili", "Giovanili_Partite.txt")
        scarica_dati(page, "t_affiliati", "Open_Partite.txt")
        
        browser.close()

if __name__ == "__main__":
    run()
