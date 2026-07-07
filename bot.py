import asyncio
import json
import logging
from playwright.async_api import async_playwright

# Configurazione logging per vedere i passaggi in tempo reale
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        
        logger.info("-> Navigazione su portale...")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        logger.info("-> Impostazione filtri...")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # Estrazione Tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        logger.info(f"-> Trovati {len(urls)} tornei.")
        
        risultati = []
        
        for i, url in enumerate(urls, 1):
            full_url = f"https://www.fitp.it{url}"
            logger.info(f"[{i}/{len(urls)}] ANALIZZO TORNEO: {full_url}")
            await page.goto(full_url, wait_until="networkidle")
            
            # Conta categorie
            dettaglio_count = await page.locator("a:has-text('Dettaglio >')").count()
            logger.info(f"   -> Trovate {dettaglio_count} categorie.")
            
            for j in range(dettaglio_count):
                # Ricarica elementi prima di cliccare
                btn = page.locator("a:has-text('Dettaglio >')").nth(j)
                await btn.click()
                await page.wait_for_load_state("networkidle")
                
                # Estrazione Giocatori
                giocatori = await page.locator("a[href*='Pagina-Giocatore']").all()
                logger.info(f"   -> Categoria {j+1}: trovati {len(giocatori)} giocatori.")
                
                for k, g_link in enumerate(giocatori, 1):
                    g_url = await g_link.get_attribute("href")
                    await page.goto(f"https://www.fitp.it{g_url}", wait_until="domcontentloaded")
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    
                    logger.info(f"      [{k}/{len(giocatori)}] Giocatore: {nome.strip()}")
                    risultati.append({"torneo": full_url, "nome": nome.strip()})
                    
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
                
                # Torna al dettaglio del torneo per la prossima categoria
                await page.goto(full_url, wait_until="networkidle")
        
        with open("Risultati_Iscrizioni.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        logger.info("-> Estrazione completata. File salvato.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
