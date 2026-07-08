import asyncio
import json
import random
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG START] Avvio modalità diagnostica ---")
    async with async_playwright() as p:
        # Browser configurato per sembrare un utente reale
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Timeout corto per forzare l'uscita in caso di ban/blocco
        page.set_default_navigation_timeout(20000)
        page.set_default_timeout(20000)

        async def human_pause():
            await asyncio.sleep(random.uniform(3, 7))

        print("--- Navigazione portale FITP ---")
        try:
            # Qui vediamo subito se il sito ci risponde o ci blocca
            response = await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
            print(f"--- Status HTTP: {response.status} ---")
            if response.status != 200:
                print(f"--- [ERRORE] Il sito ha risposto con codice {response.status}. Possibile ban. ---")
                return
        except Exception as e:
            print(f"--- [ERRORE] Navigazione fallita: {e} ---")
            return

        await human_pause()

        # Filtri con controlli
        print("--- Impostazione Filtri ---")
        try:
            await page.click('button[data-id="select_status"]')
            await page.locator('span:text-is("In programma")').last.click()
            await human_pause()
            
            await page.click('button[data-id="id_regioneSearch"]')
            await page.locator('span:text-is("Lazio")').last.click()
            await human_pause()
            
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.locator('span:text-is("Roma")').last.click()
            await human_pause()
            
            await page.click('#btn-search')
            print("--- Ricerca avviata ---")
            await asyncio.sleep(8)
        except Exception as e:
            print(f"--- Errore durante filtri: {e} ---")
            return

        # Caricamento lista
        print("--- Caricamento tornei ---")
        while True:
            btn = page.locator("button#btn-loadMore")
            if await btn.is_visible() and await btn.is_enabled():
                await btn.click()
                print("--- Cliccato 'Carica altri' ---")
                await asyncio.sleep(4)
            else:
                break
        
        # Estrazione
        urls = await page.evaluate('Array.from(document.querySelectorAll("a[href*=\'Dettaglio-Competizione\']")).map(a => a.href)')
        urls = list(set(urls))
        print(f"--- Trovati {len(urls)} tornei ---")
        
        dati_giov, dati_open = [], []
        
        for url in urls:
            try:
                await page.goto(url)
                await human_pause()
                
                btn_dettagli = page.locator("text=Dettaglio >")
                count = await btn_dettagli.count()
                
                for i in range(count):
                    btn = btn_dettagli.nth(i)
                    await btn.click()
                    await asyncio.sleep(2)
                    
                    cat = await page.locator("h1.cc-title-main").first.text_content()
                    nomi = await page.evaluate("() => Array.from(document.querySelectorAll('.cc-content-value')).map(el => el.innerText.trim())")
                    
                    entry = {"torneo": url, "categoria": cat.strip(), "iscritti": nomi}
                    if any(k in cat.lower() for k in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                        dati_giov.append(entry)
                    else:
                        dati_open.append(entry)
                    
                    await page.go_back()
                    await asyncio.sleep(2)
            except:
                continue

        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        print("--- [LOG END] Fine ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
