import asyncio
import json
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

async def run_bot():
    logger.info("--- Avvio Bot: Estrazione Iscrizioni Aperte ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        logger.info(f"Navigazione su: {BASE_URL}")
        await page.goto(BASE_URL, wait_until="networkidle")
        
        # Filtri
        await page.click('button[data-id="select_status"]')
        await page.locator('span.filter-option:has-text("Iscrizioni Aperte")').click()
        logger.info("Filtro stato: 'Iscrizioni Aperte' applicato.")
        
        await page.click('button[data-id="id_regioneSearch"]')
        await page.locator('span.filter-option:has-text("Lazio")').click()
        logger.info("Filtro regione: 'Lazio' applicato.")
        
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # Caricamento dinamico
        while await page.locator("#btn-loadMore").is_visible():
            logger.info("Caricamento altri tornei...")
            await page.click("#btn-loadMore")
            await asyncio.sleep(2)
            
        links = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in links]))
        logger.info(f"Trovati {len(urls)} tornei.")
        
        risultati = []
        for i, url_path in enumerate(urls, 1):
            full_url = f"https://www.fitp.it{url_path}"
            logger.info(f"[{i}/{len(urls)}] ACCESSO TORNEO: {full_url}")
            
            try:
                await page.goto(full_url, wait_until="networkidle")
                nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").first.text_content()
                
                giocatori_links = await page.locator("a[href*='Pagina-Giocatore']").all()
                lista_nomi = []
                
                for j, link_giocatore in enumerate(giocatori_links, 1):
                    url_g = await link_giocatore.get_attribute("href")
                    full_url_g = f"https://www.fitp.it{url_g}"
                    logger.info(f"  -> [{j}/{len(giocatori_links)}] VISITA GIOCATORE: {full_url_g}")
                    
                    await page.goto(full_url_g)
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    lista_nomi.append(nome.strip())
                    await page.go_back()
                
                risultati.append({"torneo": nome_torneo.strip(), "iscritti": lista_nomi})
                
            except Exception as e:
                logger.error(f"Errore durante analisi torneo {full_url}: {e}")
        
        with open("Iscrizioni_Aperte_Dettaglio.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        logger.info("--- Salvataggio completato: Iscrizioni_Aperte_Dettaglio.json ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
