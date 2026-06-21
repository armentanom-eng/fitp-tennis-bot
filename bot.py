import asyncio
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
OUTPUT_FILE = "Tornei_e_Iscritti.json"

async def estrai_iscritti_u14(page, url_torneo):
    """
    Funzione di estrazione con log dettagliato che include il link del torneo.
    """
    print(f"    [LOG] -> Entro nella pagina: {url_torneo}", flush=True)
    
    try:
        # Attendiamo che l'elemento categoria sia presente
        # Usiamo un selettore più generico per essere sicuri
        print(f"    [LOG] Ricerca categoria 'Singolare Femminile Under 14'...", flush=True)
        categoria = page.get_by_text("Singolare Femminile Under 14", exact=False).first
        
        if await categoria.count() == 0:
            print(f"    [LOG] ! Categoria non trovata per {url_torneo}", flush=True)
            return None
            
        print(f"    [LOG] Categoria trovata, clicco...", flush=True)
        await categoria.click()
        
        # Attesa dinamica per i nomi
        print(f"    [LOG] Attendo lista iscritti...", flush=True)
        try:
            await page.wait_for_selector(".cc-name", timeout=10000)
            
            # Estrazione nomi
            nomi_elementi = page.locator(".cc-name")
            nomi = await nomi_elementi.all_text_contents()
            lista_pulita = [n.strip() for n in nomi if n.strip()]
            
            print(f"    [LOG] [OK] Trovati {len(lista_pulita)} iscritti.", flush=True)
            return lista_pulita
            
        except Exception as e:
            print(f"    [LOG] ! Errore: Nomi non caricati. Forse la categoria è vuota? ({e})", flush=True)
            return None
            
    except Exception as e:
        print(f"    [LOG] ! Errore critico su {url_torneo}: {e}", flush=True)
        return None

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    dati_finali = {}
    
    async with async_playwright() as p:
        # OBBLIGATORIO: headless=True per GitHub Actions
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context()
        
        page = await context.new_page()
        print(f"    [LOG] Navigo su {BASE_URL}", flush=True)
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(5) 
        
        # Recupero link tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        links = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"    [LOG] Trovati {len(links)} tornei da processare.", flush=True)
        
        for link in links:
            full_url = f"https://www.fitp.it{link}"
            
            try:
                print(f"\n    [LOG] === ANALISI TORNEO ===", flush=True)
                print(f"    [LOG] Link: {full_url}", flush=True)
                
                await page.goto(full_url, wait_until="domcontentloaded")
                await asyncio.sleep(3) # Pausa necessaria per caricamento SPA
                
                iscritti = await estrai_iscritti_u14(page, full_url)
                
                if iscritti:
                    dati_finali[full_url] = iscritti
                
            except Exception as e: 
                print(f"    [LOG] ! Errore durante elaborazione {full_url}: {e}", flush=True)
        
        # Salvataggio
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dati_finali, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print(f"\n--- Bot completato. File salvato. ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
