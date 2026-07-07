import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG] START: Avvio bot In_Programma ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("--- [LOG] Navigazione a Ricerca-tornei ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        
        # Filtri
        print("--- [LOG] Applicazione filtri (In programma, Lazio, Roma) ---")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await asyncio.sleep(2)
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Caricamento lista
        print("--- [LOG] Caricamento lista tornei ---")
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            print("--- [LOG] Cliccato 'Carica altri' ---")
            await asyncio.sleep(2)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        print(f"--- [LOG] Trovati {len(urls)} tornei totali ---")
        
        dati_iscritti_giov = {"tornei": []}
        dati_iscritti_open = {"tornei": []}
        dati_partite_giov = {"tornei": []}
        dati_partite_open = {"tornei": []}
        
        for idx, url in enumerate(urls):
            print(f"--- [LOG] ({idx+1}/{len(urls)}) Analisi torneo: {url} ---")
            await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
            
            # Selezione data
            select = page.locator("select#select-ordergame")
            if await select.is_visible():
                print("--- [LOG] Menu data trovato, seleziono ultima data ---")
                await select.select_option(index=-1)
                await asyncio.sleep(2)
            
            # Categorie
            dettagli_btn = page.locator("span:has-text('Dettaglio >')")
            count = await dettagli_btn.count()
            print(f"--- [LOG] Trovate {count} categorie in questo torneo ---")
            
            for i in range(count):
                btn = page.locator("span:has-text('Dettaglio >')").nth(i)
                await btn.click()
                await asyncio.sleep(2)
                
                cat_name = await page.locator("h1.cc-title-main").first.text_content()
                print(f"--- [LOG] Analizzo categoria: {cat_name.strip()} ---")
                
                # Iscritti (usando il selettore che hai ispezionato nello screenshot)
                nomi = await page.locator("div.cc-title").all_text_contents()
                print(f"--- [LOG] Trovati {len(nomi)} iscritti ---")
                
                # ... [Aggiungi qui la logica di popolamento liste dati_iscritti_...] ...
                
                await page.go_back()
                await asyncio.sleep(2)
        
        # Salvataggio
        print("--- [LOG] Salvataggio JSON ---")
        # ... [Aggiungi qui i tuoi with open...] ...
        await browser.close()
        print("--- [LOG] FINE ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
