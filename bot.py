import asyncio
import json
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_bot():
    logger.info("--- Avvio Bot: Filtri precisi ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # 1. Filtro Stato: Iscrizioni Aperte
        # Clicchiamo il bottone specifico usando il data-id che hai mostrato
        await page.click('button[data-id="select_status"]')
        # Clicchiamo l'opzione specifica dentro il menu
        await page.locator('span.filter-option:has-text("Iscrizioni Aperte")').click()
        
        # 2. Filtro Regione: Lazio
        await page.click('button[data-id="id_regioneSearch"]')
        await page.locator('span.filter-option:has-text("Lazio")').click()
        
        # Conferma
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # Ora il caricamento è diretto
        while await page.locator("#btn-loadMore").is_visible():
            await page.click("#btn-loadMore")
            await asyncio.sleep(2)
            
        # Estrazione (come abbiamo concordato, navigando nei profili)
        links = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in links]))
        
        # ... (prosegui con la logica di estrazione iscritti tramite i link dei giocatori)
        logger.info(f"Filtri applicati, trovati {len(urls)} tornei.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
