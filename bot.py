import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
OUTPUT_FILE = "Tornei_e_Iscritti.json"

async def estrai_iscritti_u14(page, url_corrente):
    """
    Interazione dinamica: clicca su 'Dettaglio' per la categoria specifica.
    La URL non cambia in questa fase.
    """
    print(f"    [LOG] [INIZIO] Analisi categoria in: {url_corrente}", flush=True)
    
    try:
        # Trova il contenitore che ha il testo e al suo interno il bottone 'Dettaglio'
        # Questo garantisce di cliccare il bottone giusto associato alla categoria
        target_card = page.locator("div:has-text('Singolare Femminile Under 14')").get_by_role("link", name="Dettaglio")
        
        if await target_card.count() == 0:
            print(f"    [LOG] [SKIP] Categoria 'Singolare Femminile Under 14' non trovata in questo torneo.", flush=True)
            return None
            
        print(f"    [LOG] [AZIONE] Clicco su 'Dettaglio' per Under 14...", flush=True)
        await target_card.first.click()
        
        # Attesa della comparsa dei nomi (.cc-name) senza cambiare pagina
        try:
            print(f"    [LOG] [ATTESA] Attendo caricamento elenco nomi...", flush=True)
            await page.wait_for_selector(".cc-name", timeout=10000)
            
            nomi = await page.locator(".cc-name").all_text_contents()
            lista_pulita = [n.strip() for n in nomi if n.strip()]
            
            print(f"    [LOG] [SUCCESS] Estratti {len(lista_pulita)} nomi.", flush=True)
            return lista_pulita
            
        except Exception as e:
            print(f"    [LOG] [ERRORE] I nomi non sono apparsi dopo il click. {e}", flush=True)
            return None
            
    except Exception as e:
        print(f"    [LOG] [CRITICO] Errore durante l'interazione: {e}", flush=True)
        return None

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    dati_finali = {}
    
    async with async_playwright() as p:
        # headless=True è OBBLIGATORIO per GitHub Actions
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"    [LOG] Navigo su {BASE_URL}...", flush=True)
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(5) 
        
        # Recupero link tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        links = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"    [LOG] Trovati {len(links)} tornei da analizzare.", flush=True)
        
        for link in links:
            full_url = f"https://www.fitp.it{link}"
            print(f"\n    [LOG] === NUOVO TORNEO: {full_url} ===", flush=True)
            
            try:
                # Navigazione (Cambia URL)
                await page.goto(full_url, wait_until="domcontentloaded")
                await asyncio.sleep(3) 
                
                # Estrazione (Non cambia URL)
                iscritti = await estrai_iscritti_u14(page, full_url)
                
                if iscritti:
                    dati_finali[full_url] = iscritti
                
            except Exception as e: 
                print(f"    [LOG] [ERRORE] Errore critico su {full_url}: {e}", flush=True)
        
        # Salvataggio
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dati_finali, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print(f"\n--- Bot completato. File {OUTPUT_FILE} salvato. ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
