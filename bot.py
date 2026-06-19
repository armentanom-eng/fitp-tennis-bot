import time
from playwright.sync_api import sync_playwright

def run():
    print("Avvio bot... Navigazione verso FITP")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Navigazione
        try:
            page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
            print("Pagina caricata.")
        except Exception as e:
            print(f"Errore navigazione: {e}")
            return

        # 2. PROVA A CHIUDERE I COOKIE (Il "Cookie Killer")
        # Cerchiamo bottoni comuni per i cookie, se esistono
        try:
            print("Controllo banner cookie...")
            # Cerca un bottone che contiene 'Accetta' o 'Accept'
            cookie_button = page.locator("button:has-text('Accetta'), button:has-text('Accept')").first
            if cookie_button.is_visible():
                cookie_button.click()
                print("Banner cookie chiuso.")
                page.wait_for_timeout(2000)
        except:
            print("Nessun banner cookie rilevato o già chiuso.")

        # 3. ESTRAZIONE DATI
        print("Cerco i tornei...")
        try:
            # Attendiamo che la lista principale sia visibile
            # Usiamo un selettore un po' più generico che punta alla tabella dei risultati
            page.wait_for_selector(".cc-row-table", timeout=20000)
            
            # Ora cerchiamo i link dentro la tabella
            links = page.query_selector_all("a[href*='Dettaglio-Competizione']")
            
            if links:
                print(f"Trovati {len(links)} tornei! Primo link: {links[0].get_attribute('href')}")
                with open("Report_Partite.txt", "w", encoding="utf-8") as f:
                    f.write(f"Successo! Trovati {len(links)} tornei.\n")
                    f.write(f"Esempio link: {links[0].get_attribute('href')}")
            else:
                with open("Report_Partite.txt", "w", encoding="utf-8") as f:
                    f.write("Pagina caricata ma nessun torneo trovato con quel selettore.")
                    
        except Exception as e:
            print(f"Errore durante l'attesa dei tornei: {e}")
            # Se fallisce, salviamo l'errore
            with open("Report_Partite.txt", "w", encoding="utf-8") as f:
                f.write(f"Errore tecnico: {str(e)}")

        browser.close()
        print("Operazione terminata.")

if __name__ == "__main__":
    run()
