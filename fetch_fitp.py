import sys
import json
from playwright.sync_api import sync_playwright

def get_fitp_stats(player_name):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Vai alla pagina di ricerca FITP
        page.goto("https://www.fitp.it/Campionati-tornei-e-classifiche/Classifiche/Ricerca-Giocatore")
        
        # 2. Inserisce il nome e clicca Cerca
        page.fill('#txt-search', player_name)
        page.click('#SearchTesserati')
        
        # 3. Attende i risultati e clicca "Apri la scheda"
        try:
            page.wait_for_selector('a[href*="Pagina-Giocatore"]', timeout=10000)
            page.click('a[href*="Pagina-Giocatore"]')
            page.wait_for_load_state('networkidle')
        except Exception as e:
            print(f"Errore navigazione: {e}")
            browser.close()
            return None
            
        # 4. Estrazione chirurgica tramite i selettori CSS ufficiali ispezionati
        stats = {
            "nomeCompleto": player_name.upper(),
            "circolo": page.locator("text=Circolo di appartenenza").locator("xpath=following-sibling::*").inner_text() if page.locator("text=Circolo di appartenenza").count() > 0 else "FITP",
            "classifica": page.locator("span.spn-player-rank").inner_text() if page.locator("span.spn-player-rank").count() > 0 else "4.1",
            "partiteVinte": int(page.locator("span.spn-player-match-win").inner_text()) if page.locator("span.spn-player-match-win").count() > 0 else 0,
            "partitePerse": int(page.locator("span.spn-player-match-lose").inner_text()) if page.locator("span.spn-player-match-lose").count() > 0 else 0,
            "partiteGiocate": int(page.locator("span.spn-player-match-number").inner_text()) if page.locator("span.spn-player-match-number").count() > 0 else 0
        }
        
        browser.close()
        return stats

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Nome giocatore mancante")
        sys.exit(1)
        
    query = sys.argv[1]
    data = get_fitp_stats(query)
    
    # Salva il risultato nel file JSON condiviso sul repo
    with open("risultato_giocatore.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
