import asyncio
import os
import json
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

async def get_iscritti(page, tab_name):
    """Estrae i nomi dalla tabella iscritti."""
    try:
        # Selettore specifico per il nome iscritto basato sul tuo screenshot
        if await page.locator("span.cc-name").first.is_visible(timeout=5000):
            elementi = await page.locator("span.cc-name").all_text_contents()
            iscritti = [nome.strip() for nome in elementi if nome.strip()]
            logger.info(f"   [OK] Trovati {len(iscritti)} iscritti in '{tab_name}'")
            return iscritti
    except Exception as e:
        logger.error(f"   [!] Errore estrazione iscritti: {e}")
    return []

async def run_bot():
    logger.info("--- Avvio Bot: Solo Iscrizioni Aperte ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(BASE_URL, wait_until="networkidle")
        
        # 1. Filtro Stato: Iscrizioni aperte
        await page.click('button[data-id="select_status"]')
        await page.locator("text='Iscrizioni aperte'").click()
        
        # 2. Filtro Regione: Lazio
        await page.click('button[data-id="id_regioneSearch"]')
        await page.locator("text='Lazio'").click()
        
        # Conferma (invio o tasto cerca se presente)
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # Caricamento risultati
        while await page.locator("#btn-loadMore").is_visible():
            await page.click("#btn-loadMore")
            await asyncio.sleep(2)
            
        links = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in links]))
        logger.info(f"Trovati {len(urls)} tornei.")
        
        risultati = []
        for url_path in urls:
            full_url = f"https://www.fitp.it{url_path}"
            logger.info(f"-> Analizzo: {full_url}")
            
            try:
                await page.goto(full_url, wait_until="networkidle")
                
                # Nome torneo
                nome = await page.locator("h1.cc-title-main.spn-competition-description").first.text_content()
                
                # Iscrizioni (tab)
                tabs = await page.locator("a[data-toggle='tab']").all()
                iscritti_data = {}
                for tab in tabs:
                    tab_name = (await tab.text_content()).strip()
                    await tab.click()
                    await asyncio.sleep(1)
                    iscritti_data[tab_name] = await get_iscritti(page, tab_name)
                
                risultati.append({"nome": nome.strip(), "url": full_url, "iscritti": iscritti_data})
                
            except Exception as e:
                logger.error(f"Errore su {full_url}: {e}")
        
        with open("Iscrizioni_Aperte.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        logger.info("--- Salvataggio completato: Iscrizioni_Aperte.json ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
