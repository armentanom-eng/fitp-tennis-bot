import time
from playwright.sync_api import sync_playwright

def run():
    print("Avvio del bot...")
    with sync_playwright() as p:
        # Avvia browser in modalità headless (senza interfaccia grafica, necessaria per GitHub)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Navigazione
        print("Navigazione verso FITP...")
        try:
            page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        except Exception as e:
            print(f"Errore nella navigazione: {e}")
            return

        # 2. SELEZIONE FILTRI
        # Se il sito chiede di accettare i cookie, il bot potrebbe bloccarsi. 
        # Inseriamo un piccolo click generico se appare un popup, o procediamo.
        try:
            print("Cerco il bottone categoria...")
            # Sostituisci 'TORNEI OPEN' con il testo esatto che vedi sul sito
            # Se vuoi 'GIOVANILI', scrivi semplicemente 'GIOVANILI'
            page.click("text='OPEN'", timeout=10000) 
            page.wait_for_timeout(5000) # Attesa di 5 secondi per caricamento dati
            print("Cliccato categoria correttamente.")
        except Exception as e:
            print(f"Bottone non trovato o errore: {e}")

        # 3. ESTRAZIONE DATI
        # Cerchiamo le 'card' o i blocchi che contengono i tornei
        # (Adattiamo il selettore se il nome della classe cambia)
        try:
            # Esempio: cerchiamo tutti gli elementi che contengono i titoli dei tornei
            # Se il sito usa tag specifici, vanno aggiornati qui
            tornei = page.query_selector_all("h3, .card-title, .torneo-nome")
            
            data_file = []
            for t in tornei:
                text = t.inner_text().strip()
                if text:
                    data_file.append(text)
            
            # 4. SALVATAGGIO
            with open("Report_Partite.txt", "w", encoding="utf-8") as f:
                f.write(f"--- REPORT ESTRATTO IL {time.strftime('%d/%m/%Y %H:%M')} ---\n\n")
                if not data_file:
                    f.write("Nessun torneo trovato. Controllare i selettori CSS.")
                else:
                    for item in data_file:
                        f.write(f"- {item}\n")
            
            print(f"Salvato {len(data_file)} elementi nel file.")
            
        except Exception as e:
            print(f"Errore durante l'estrazione: {e}")

        browser.close()
        print("Operazione completata.")

if __name__ == "__main__":
    run()
