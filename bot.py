import time
from playwright.sync_api import sync_playwright

def run():
    print("Avvio bot... Navigazione verso FITP")
    with sync_playwright() as p:
        # Avvia il browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Vai alla pagina di ricerca
        page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # 2. Clicca sul primo torneo della lista (Dettagli)
        # Il selettore cerca il link che contiene 'Dettaglio-Competizione'
        print("Cerco il primo torneo disponibile...")
        try:
            # Attendiamo che appaia almeno un link di dettaglio
            page.wait_for_selector("a[href*='Dettaglio-Competizione']", timeout=15000)
            
            # Clicchiamo il primo che troviamo
            dettaglio_link = page.query_selector("a[href*='Dettaglio-Competizione']")
            dettaglio_link.click()
            print("Entrato nella pagina Dettagli.")
            
            # 3. Aspettiamo che si carichi la pagina di dettaglio
            page.wait_for_load_state("networkidle")
            
            # 4. Cerchiamo il bottone Scarica (ID identificato: btnOrderGameDownload)
            print("Cerco il bottone Scarica...")
            page.wait_for_selector("#btnOrderGameDownload", timeout=15000)
            
            # Verifichiamo se il bottone esiste
            bottone_scarica = page.query_selector("#btnOrderGameDownload")
            if bottone_scarica:
                print("TROVATO! Il bottone Scarica è presente.")
                # Nota: In headless mode il download automatico è complesso.
                # Per ora verifichiamo che il bot arrivi qui.
                with open("Report_Partite.txt", "w", encoding="utf-8") as f:
                    f.write("Successo: Il bot ha trovato il bottone di download per il torneo.")
            
        except Exception as e:
            print(f"Errore durante la navigazione: {e}")
            # Salviamo l'errore nel report per capire dove si ferma
            with open("Report_Partite.txt", "w", encoding="utf-8") as f:
                f.write(f"Errore: {str(e)}")

        browser.close()
        print("Operazione terminata.")

if __name__ == "__main__":
    run()
