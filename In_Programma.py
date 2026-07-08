import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio bot con logica collaudata ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        print("--- Navigazione portale FITP ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # FILTRI (Uso di selettori stabili come nel codice testato)
        print("--- Impostazione Filtri ---")
        await page.click('button[data-id="select_status"]')
        await page.locator('span:text-is("In programma")').last.click()
        
        await page.click('button[data-id="id_regioneSearch"]')
        await page.locator('span:text-is("Lazio")').last.click()
        
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.locator('span:text-is("Roma")').last.click()
        
        await page.click('#btn-search')
        await asyncio.sleep(5)
        
        # CARICAMENTO LISTA
        print("--- Caricamento totale lista tornei ---")
        while True:
            btn = page.locator("button#btn-loadMore")
            if await btn.is_visible():
                print("    -> Trovato 'Carica altri', clicco...")
                await btn.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
            else:
                print("    -> Lista completa caricata.")
                break
        
        # ESTRAZIONE URL
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. Inizio estrazione dati. ---")
        
        dati_giov = {"tornei": []}
        dati_open = {"tornei": []}
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}" if url.startswith('/') else url
            try:
                await page.goto(full_url, wait_until="networkidle")
                
                # Numero di bottoni Dettaglio presenti
                dettagli = page.locator("text=Dettaglio >")
                count = await dettagli.count()
                print(f"--- Analisi: {full_url} ({count} categorie) ---")
                
                for i in range(count):
                    btn = page.locator("text=Dettaglio >").nth(i)
                    cat_nome = await btn.evaluate("el => el.parentElement.innerText.split('Dettaglio')[0].trim()")
                    
                    await btn.click()
                    await page.wait_for_load_state("networkidle")
                    
                    # Estrazione nomi
                    nomi = await page.evaluate("""() => Array.from(document.querySelectorAll('.cc-content-value'))
                        .map(el => el.innerText.trim())
                        .filter(t => /^[A-Z\s'À-ÖØ-öø-ÿ]+$/.test(t) && t.length > 3)""")
                    
                    entry = {"torneo": full_url, "categoria": cat_nome, "iscritti": sorted(list(set(nomi)))}
                    
                    if any(k in cat_nome.lower() for k in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                        dati_giov["tornei"].append(entry)
                    else:
                        dati_open["tornei"].append(entry)
                    
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"    ! Errore su {full_url}: {e}")
                continue
        
        # SALVATAGGIO
        with open("Iscritti_Giovanili.json", "w", encoding="utf-8") as f:
            json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open.json", "w", encoding="utf-8") as f:
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato. File salvati. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
