import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG] Avvio del bot In_Programma ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("--- [LOG] Navigazione pagina iniziale ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        
        # Filtri
        print("--- [LOG] Applicazione filtri ---")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(2)
        
        # Caricamento lista
        print("--- [LOG] Espansione lista tornei ---")
        while await page.locator("button#btn-loadMore").is_visible():
            print("--- [LOG] Clicco Carica Altri ---")
            await page.click("button#btn-loadMore")
            await asyncio.sleep(1)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        print(f"--- [LOG] Trovati {len(urls)} tornei. Inizio estrazione. ---")
        
        # ... (Mantieni qui la logica delle liste e il ciclo for precedente) ...
        # IMPORTANTE: Nel ciclo, usa solo await page.goto(..., wait_until="domcontentloaded")
        # Rimuovi ogni "networkidle" dal ciclo!

        # ... (Salvataggio file) ...
        print("--- [LOG] Salvataggio completato ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
