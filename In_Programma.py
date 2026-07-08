import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Deep Scraper FITP - Separazione Open/Giovanili ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        await asyncio.sleep(5)
        
        # Filtri (Status, Regione, Provincia)
        for selector in ['button[data-id="select_status"]', 'button[data-id="id_regioneSearch"]', 'button[data-id="id_provinciaSearch"]']:
            await page.locator(selector).click()
            await asyncio.sleep(1)
            await page.locator('span.text').last.click()
            await asyncio.sleep(1)
        
        await page.locator('#btn-search').click()
        await asyncio.sleep(5)
        
        # Carica tutta la lista
        while True:
            btn = await page.query_selector('button#btn-loadMore')
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(3)
            else: break
        
        urls = await page.evaluate('Array.from(document.querySelectorAll("a[href*=\'Dettaglio-Competizione\']")).map(a => a.href)')
        unique_urls = list(set(urls))
        
        data_open, data_giov = [], []
        
        for url in unique_urls:
            try:
                await page.goto(url)
                await asyncio.sleep(3)
                
                nome_torneo = await page.evaluate('document.querySelector(".cc-title-main")?.innerText.trim() || "Torneo"')
                
                cat_buttons = await page.query_selector_all('span:has-text("Dettaglio >")')
                dettagli_torneo = []
                
                for btn in cat_buttons:
                    categoria = await btn.evaluate("el => el.parentElement.innerText.split('Dettaglio')[0].trim()")
                    await btn.click()
                    await asyncio.sleep(3)
                    
                    nomi = await page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('.cc-content-value'))
                            .map(el => el.innerText.trim())
                            .filter(t => /^[A-Z\s'À-ÖØ-öø-ÿ]+$/.test(t) && t.length > 3);
                    }""")
                    
                    dettagli_torneo.append({"categoria": categoria, "partecipanti": sorted(list(set(nomi)))})
                    await page.go_back()
                    await asyncio.sleep(3)
                
                entry = {"torneo": nome_torneo, "dettagli": dettagli_torneo}
                
                # Logica di separazione
                if any(k in nome_torneo.lower() for k in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                    data_giov.append(entry)
                else:
                    data_open.append(entry)
                    
                print(f"--- [OK] Analizzato: {nome_torneo[:20]} ---")
            except: continue

        # Salvataggio separato
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_open, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_giov, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        print("--- [END] Processo terminato: file Open e Giovanili aggiornati ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
