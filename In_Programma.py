import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG START] Avvio bot con correzione blocco caricamento ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        page.set_default_timeout(45000)
        
        # 1. Navigazione e Filtri
        print("--- Navigazione e filtri ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        await page.click('button[data-id="select_status"]')
        await page.locator('span:text-is("In programma")').last.click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.locator('span:text-is("Lazio")').last.click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.locator('span:text-is("Roma")').last.click()
        await page.click('#btn-search')
        await asyncio.sleep(5)
        
        # 2. Caricamento lista (Con controllo is_enabled)
        print("--- Caricamento lista tornei ---")
        while True:
            btn = page.locator("button#btn-loadMore")
            # Controlliamo sia visibilità che stato abilitato
            if await btn.is_visible() and await btn.is_enabled():
                print("    -> Bottone attivo, clicco...")
                await btn.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
            else:
                print("    -> Lista completa o bottone disabilitato.")
                break
        
        # 3. Estrazione URL
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. Inizio estrazione ---")
        
        dati_giov, dati_open = [], []
        
        # 4. Analisi tornei
        for url in urls:
            full_url = f"https://www.fitp.it{url}" if url.startswith('/') else url
            try:
                print(f"--- Analizzo torneo: {full_url[-20:]} ---")
                await page.goto(full_url, wait_until="networkidle")
                
                count = await page.locator("text=Dettaglio >").count()
                
                for i in range(count):
                    btn = page.locator("text=Dettaglio >").nth(i)
                    await btn.click()
                    await page.wait_for_load_state("networkidle")
                    
                    cat_nome = await page.locator("h1.cc-title-main").first.text_content()
                    nomi = await page.evaluate("""() => Array.from(document.querySelectorAll('.cc-content-value'))
                        .map(el => el.innerText.trim()).filter(t => t.length > 3)""")
                    
                    entry = {"torneo": full_url, "categoria": cat_nome.strip(), "iscritti": sorted(list(set(nomi)))}
                    if any(k in cat_nome.lower() for k in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                        dati_giov.append(entry)
                    else:
                        dati_open.append(entry)
                    
                    # Ritorno alla pagina principale del torneo
                    await page.goto(full_url, wait_until="networkidle")
                    
            except Exception as e:
                print(f"--- Errore su {full_url}: {e} ---")
                continue
        
        # 5. Salvataggio
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        print("--- [LOG END] Processo completato correttamente ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
