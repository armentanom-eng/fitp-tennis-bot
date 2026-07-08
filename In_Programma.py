import asyncio
import json
import random
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG START] Avvio modalità prudente ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        # Funzione helper per pause umane
        async def human_pause():
            await asyncio.sleep(random.uniform(5, 10))

        print("--- Navigazione portale FITP ---")
        try:
            response = await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
            print(f"--- Status Codice: {response.status} ---")
            if response.status != 200:
                print("--- [ALLERTA] Il sito sta restituendo un codice di errore! ---")
        except Exception as e:
            print(f"--- Errore navigazione: {e} ---")
            await page.screenshot(path="errore_navigazione.png")
            return

        await human_pause()

        # FILTRI (con attese umane)
        print("--- Impostazione Filtri ---")
        try:
            await page.click('button[data-id="select_status"]')
            await human_pause()
            await page.locator('span:text-is("In programma")').last.click()
            await human_pause()
            
            await page.click('button[data-id="id_regioneSearch"]')
            await human_pause()
            await page.locator('span:text-is("Lazio")').last.click()
            await human_pause()
            
            await page.click('button[data-id="id_provinciaSearch"]')
            await human_pause()
            await page.locator('span:text-is("Roma")').last.click()
            await human_pause()
            
            await page.click('#btn-search')
            print("--- Ricerca avviata ---")
            await human_pause()
        except Exception as e:
            print(f"--- Errore filtri: {e} ---")
            await page.screenshot(path="errore_filtri.png")
            return

        # CARICAMENTO
        print("--- Controllo caricamento tornei ---")
        while True:
            btn = page.locator("button#btn-loadMore")
            if await btn.is_visible() and await btn.is_enabled():
                await btn.click()
                await human_pause()
            else:
                break
        
        # ESTRAZIONE
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. ---")
        
        dati_giov, dati_open = [], []
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}" if url.startswith('/') else url
            try:
                await page.goto(full_url, wait_until="networkidle")
                await human_pause()
                
                count = await page.locator("text=Dettaglio >").count()
                for i in range(count):
                    btn = page.locator("text=Dettaglio >").nth(i)
                    await btn.click()
                    await human_pause()
                    
                    cat_nome = await page.locator("h1.cc-title-main").first.text_content()
                    nomi = await page.evaluate("""() => Array.from(document.querySelectorAll('.cc-content-value'))
                        .map(el => el.innerText.trim()).filter(t => t.length > 3)""")
                    
                    entry = {"torneo": full_url, "categoria": cat_nome.strip(), "iscritti": sorted(list(set(nomi)))}
                    if any(k in cat_nome.lower() for k in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                        dati_giov.append(entry)
                    else:
                        dati_open.append(entry)
                    
                    await page.goto(full_url, wait_until="networkidle")
            except Exception as e:
                print(f"--- Errore su {url}: {e} ---")
                continue
        
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        print("--- [LOG END] Processo completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
