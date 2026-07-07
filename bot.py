import asyncio
import os
import pdfplumber
import re
import json
import logging
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {
    "t_giovanili": "Giovanili_Partite.json", 
    "t_affiliati": "Open_Partite.json"
}
STATUSES = ["In corso", "Iscrizioni aperte"]

# ... (Mantieni le funzioni format_line_for_swift e get_pdf_info invariate)

async def get_iscritti(page, tab_name):
    iscritti = []
    try:
        # Attendiamo che la tabella sia presente
        if await page.locator("span.cc-name").first.is_visible(timeout=5000):
            elementi = await page.locator("span.cc-name").all_text_contents()
            iscritti = [nome.strip() for nome in elementi if nome.strip()]
            logger.info(f"   [OK] Trovati {len(iscritti)} iscritti nella tab '{tab_name}'")
        else:
            logger.warning(f"   [!] Nessun nome trovato in '{tab_name}'")
    except Exception as e:
        logger.error(f"   [!] Errore estrazione iscritti: {e}")
    return iscritti

async def run_bot():
    logger.info("--- Avvio Bot ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        start_date_filter = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        
        for cat_id, filename in CATEGORIES.items():
            logger.info(f"--- Sessione: {filename} ---")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}

            for status in STATUSES:
                page = await context.new_page()
                await page.goto(BASE_URL, wait_until="networkidle")
                
                # Clicca il selettore stato e seleziona l'opzione
                await page.click('button[data-id="select_status"]')
                await page.wait_for_selector(".dropdown-menu.show")
                await page.click(f"text='{status}'") 
                
                # Seleziona Regione Lazio
                await page.click('button[data-id="id_regioneSearch"]')
                await page.wait_for_selector(".dropdown-menu.show")
                await page.click("text='Lazio'")
                
                await page.fill("#dpk_start_date", start_date_filter)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                await page.click(f'a[data-id="{cat_id}"]')
                await asyncio.sleep(3)

                # Carica tornei
                while await page.locator("#btn-loadMore").is_visible():
                    await page.click("#btn-loadMore")
                    await asyncio.sleep(2)
                
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    logger.info(f"-> Analizzo: {full_url}")
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        
                        # Estrazione iscritti (usando selettore tab generico)
                        tabs = await page.locator("a[data-toggle='tab']").all()
                        iscritti_dict = {}
                        for tab in tabs:
                            name = (await tab.text_content()).strip()
                            await tab.click()
                            await asyncio.sleep(1)
                            iscritti_dict[name] = await get_iscritti(page, name)
                        
                        json_data["tornei"].append({"url": full_url, "iscritti": iscritti_dict})
                    except Exception as e:
                        logger.error(f"Errore su {full_url}: {e}")
                
                await page.close()
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
