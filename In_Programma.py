import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG: AVVIO] ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()
        
        print("--- [LOG: Navigazione] ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        await asyncio.sleep(8)
        
        # FILTRI SPECIFICI (Non più generici)
        print("--- [LOG: Applicazione Filtri] ---")
        
        # Filtro Stato
        await page.locator('button[data-id="select_status"]').click()
        await page.locator('span:text-is("In programma")').last.click()
        print("--- [LOG: Filtro Stato impostato] ---")
        
        # Filtro Regione
        await page.locator('button[data-id="id_regioneSearch"]').click()
        await page.locator('span:text-is("Lazio")').last.click()
        print("--- [LOG: Filtro Regione impostato] ---")
        
        # Filtro Provincia
        await page.locator('button[data-id="id_provinciaSearch"]').click()
        await page.locator('span:text-is("Roma")').last.click()
        print("--- [LOG: Filtro Provincia impostato] ---")
        
        await page.locator('#btn-search').click()
        await asyncio.sleep(5)
        
        # Caricamento
        print("--- [LOG: Caricamento lista tornei...] ---")
        while True:
            btn = await page.query_selector('button#btn-loadMore')
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(3)
            else: break
        
        urls = await page.evaluate('Array.from(document.querySelectorAll("a[href*=\'Dettaglio-Competizione\']")).map(a => a.href)')
        unique_urls = list(set(urls))
        print(f"--- [LOG: Trovati {len(unique_urls)} tornei] ---")
        
        data_open, data_giov = [], []
        
        for url in unique_urls:
            try:
                await page.goto(url)
                await asyncio.sleep(3)
                nome = await page.evaluate('document.querySelector(".cc-title-main")?.innerText.trim() || "Torneo"')
                print(f"--- [LOG: Analisi: {nome[:25]}] ---")
                
                cat_buttons = await page.query_selector_all('text=Dettaglio >')
                dettagli = []
                for btn in cat_buttons:
                    # Estrai categoria
                    cat_nome = await btn.evaluate("el => el.parentElement.innerText.split('Dettaglio')[0].trim()")
                    await btn.click()
                    await asyncio.sleep(2)
                    
                    nomi = await page.evaluate("""() => Array.from(document.querySelectorAll('.cc-content-value')).map(el => el.innerText.trim()).filter(t => /^[A-Z\s'À-ÖØ-öø-ÿ]+$/.test(t) && t.length > 3)""")
                    dettagli.append({"categoria": cat_nome, "partecipanti": sorted(list(set(nomi)))})
                    print(f"    -> {cat_nome}: {len(nomi)} iscritti")
                    await page.go_back()
                    await asyncio.sleep(2)
                
                entry = {"torneo": nome, "dettagli": dettagli}
                if any(k in nome.lower() for k in ["under", "u10", "u12", "u14", "u16", "giovanile"]): data_giov.append(entry)
                else: data_open.append(entry)
            except Exception as e:
                print(f"--- [LOG: ERRORE {nome}] ---")
                continue

        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(data_open, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f: json.dump(data_giov, f, ensure_ascii=False, indent=4)
        
        print("--- [LOG: FINE] ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
