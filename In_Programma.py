import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Scraper Definitivo - Versione Stealth Corretta ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        await asyncio.sleep(8)
        
        # Filtri
        await page.locator('button[data-id="select_status"]').click()
        await page.locator('span:text-is("In programma")').last.click()
        await page.locator('button[data-id="id_regioneSearch"]').click()
        await page.locator('span:text-is("Lazio")').last.click()
        await page.locator('button[data-id="id_provinciaSearch"]').click()
        await page.locator('span:text-is("Roma")').last.click()
        await page.locator('#btn-search').click()
        await asyncio.sleep(5)
        
        # Caricamento completo - CORRETTO
        while True:
            # Qui mancava l'await su query_selector
            btn = await page.query_selector('button#btn-loadMore')
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(3)
            else: 
                break
        
        # Recupero URL
        urls = await page.evaluate('Array.from(document.querySelectorAll("a[href*=\'Dettaglio-Competizione\']")).map(a => a.href)')
        unique_urls = list(set(urls))
        
        data_giov, data_open = [], []
        
        for url in unique_urls:
            try:
                await page.goto(url)
                await asyncio.sleep(4)
                nome = await page.evaluate('document.querySelector(".cc-title-main")?.innerText.trim() || "Torneo"')
                
                bottoni = await page.query_selector_all('text=Dettaglio >')
                tabelloni = []
                for i in range(len(bottoni)):
                    # Ricarichiamo i bottoni ad ogni giro per evitare errori
                    btns = await page.query_selector_all('text=Dettaglio >')
                    nome_cat = await btns[i].evaluate("el => el.parentElement.innerText.split('\\n')[0].trim()")
                    await btns[i].click()
                    await asyncio.sleep(2)
                    
                    nomi = await page.evaluate("""() => Array.from(document.querySelectorAll('.cc-content-value')).map(el => el.innerText.trim()).filter(t => t.length > 5 && /^[A-Z\s'À-ÖØ-öø-ÿ]+$/.test(t))""")
                    
                    tabelloni.append({"categoria": nome_cat, "iscritti": sorted(list(set(nomi)))})
                    await page.go_back()
                    await asyncio.sleep(2)
                
                entry = {"torneo": nome, "dettagli": tabelloni}
                if any(k in nome.lower() for k in ["under", "u10", "u12", "u14", "u16", "giovanile"]): data_giov.append(entry)
                else: data_open.append(entry)
                print(f"--- [OK] {nome[:20]} | Tabelloni: {len(tabelloni)} ---")
            except Exception as e:
                print(f"--- [ERRORE] {url}: {e} ---")
                continue

        with open("Iscritti_In_Programma.json", "w", encoding="utf-8") as f: json.dump(data_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(data_open, f, ensure_ascii=False, indent=4)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
