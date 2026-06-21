import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
OUTPUT_FILE = "Tornei_e_Iscritti.json"

async def estrai_iscritti_u14(page, url_torneo):
    print(f"    [LOG] Tentativo estrazione su: {url_torneo}", flush=True)
    
    try:
        # Cerca il blocco che contiene il testo della categoria
        categoria_locator = page.locator("div:has-text('Singolare Femminile Under 14')").first
        
        if await categoria_locator.count() == 0:
            print(f"    [LOG] Categoria non trovata.", flush=True)
            return None
            
        print(f"    [LOG] Categoria trovata, clicco...", flush=True)
        await categoria_locator.click()
        
        # Attesa specifica per la comparsa dei nomi (.cc-name)
        try:
            await page.wait_for_selector(".cc-name", timeout=8000)
            nomi = await page.locator(".cc-name").all_text_contents()
            lista_pulita = [n.strip() for n in nomi if n.strip()]
            
            print(f"    [LOG] [SUCCESS] Estratti {len(lista_pulita)} nomi.", flush=True)
            return lista_pulita
            
        except Exception:
            print(f"    [LOG] Nessun nome apparso dopo il click.", flush=True)
            return None
            
    except Exception as e:
        print(f"    [LOG] Errore critico: {e}", flush=True)
        return None

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    dati_finali = {}
    
    async with async_playwright() as p:
        # headless=True è OBBLIGATORIO per GitHub
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"    [LOG] Navigo su {BASE_URL}...", flush=True)
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(5) 
        
        # Recupero link tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        links = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"    [LOG] Trovati {len(links)} tornei.", flush=True)
        
        for link in links:
            full_url = f"https://www.fitp.it{link}"
            try:
                await page.goto(full_url, wait_until="domcontentloaded")
                await asyncio.sleep(3) 
                
                iscritti = await estrai_iscritti_u14(page, full_url)
                if iscritti:
                    dati_finali[full_url] = iscritti
                
            except Exception as e: 
                print(f"    [LOG] Errore su {full_url}: {e}", flush=True)
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dati_finali, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print(f"\n--- Bot completato. File {OUTPUT_FILE} salvato. ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
