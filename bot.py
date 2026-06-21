import asyncio
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# --- CONFIGURAZIONE ---
URL_RICERCA = "https://www.fitp.it/Tornei/Ricerca-tornei"
FILE_OUTPUT = "risultati_iscritti.json"
DATA_INIZIO = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
CATEGORIA_TARGET = "Singolare Femminile Under 14"

async def main():
    print(f"[LOG] Avvio script...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"[LOG] Navigazione su: {URL_RICERCA}", flush=True)
        await page.goto(URL_RICERCA, wait_until="networkidle")
        
        # 1. Imposta la data
        print(f"[LOG] Imposto data inizio: {DATA_INIZIO}", flush=True)
        await page.fill("#dpk_start_date", DATA_INIZIO)
        
        # 2. Clicca cerca (adatta il selettore se necessario)
        print(f"[LOG] Eseguo ricerca...", flush=True)
        # Assicurati di cliccare il bottone di ricerca dopo aver inserito la data
        await page.keyboard.press("Enter") 
        await asyncio.sleep(5) # Attesa per caricamento risultati
        
        # 3. Ottieni i link dei tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        links = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"[LOG] Trovati {len(links)} tornei. Analizzo...", flush=True)
        
        risultati = []

        for link in links:
            full_url = f"https://www.fitp.it{link}"
            print(f"[LOG] Entro in: {full_url}", flush=True)
            
            try:
                # Apro una nuova pagina per il torneo
                page_torneo = await browser.new_page()
                await page_torneo.goto(full_url, wait_until="networkidle")
                
                # Controllo categorie (cerchiamo il testo parziale)
                # Troviamo tutti i blocchi categoria
                categorie = await page_torneo.locator(".cc-single-tournament").all()
                trovato = False
                
                for cat in categorie:
                    testo = await cat.text_content()
                    if CATEGORIA_TARGET in testo:
                        print(f"[LOG] Categoria '{CATEGORIA_TARGET}' trovata in questo torneo.", flush=True)
                        await cat.get_by_role("link", name="Dettaglio").click()
                        await page_torneo.wait_for_load_state("networkidle")
                        
                        # Estrazione iscritti
                        if await page_torneo.locator(".cc-section-participants").is_visible(timeout=5000):
                            nomi = await page_torneo.locator(".cc-name").all_text_contents()
                            lista_pulita = [n.strip() for n in nomi if n.strip()]
                            risultati.append({"url": full_url, "iscritti": lista_pulita})
                            print(f"[LOG] Estratti {len(lista_pulita)} giocatori.", flush=True)
                        
                        trovato = True
                        break
                
                if not trovato:
                    print(f"[LOG] Categoria non presente in questo torneo. Salto.", flush=True)
                
                await page_torneo.close()
                
            except Exception as e:
                print(f"[ERRORE] Impossibile elaborare {full_url}: {e}", flush=True)

        # 4. Salvataggio
        with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        print(f"[LOG] Operazione completata. Dati salvati in {FILE_OUTPUT}", flush=True)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
