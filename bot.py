import asyncio
import json
import logging
from playwright.async_api import async_playwright

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_bot():
    async with async_playwright() as p:
        # Configurazione essenziale per GitHub Actions
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        
        logger.info("Navigazione su portale...")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri (usa la logica che sappiamo funzionare)
        logger.info("Impostazione filtri...")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
        
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # Estrazione tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        logger.info(f"Trovati {len(urls)} tornei.")
        
        risultati = []
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            await page.goto(full_url, wait_until="networkidle")
            
            # Trova i bottoni "Dettaglio >" per ogni categoria
            dettaglio_links = await page.locator("a:has-text('Dettaglio >')").count()
            
            for i in range(dettaglio_links):
                # Ricarichiamo i selettori per evitare problemi dopo la navigazione
                links = page.locator("a:has-text('Dettaglio >')")
                await links.nth(i).click()
                await page.wait_for_load_state("networkidle")
                
                # Estrazione giocatori nella categoria
                giocatori = await page.locator("a[href*='Pagina-Giocatore']").all()
                for g_link in giocatori:
                    g_url = await g_link.get_attribute("href")
                    
                    # Vai alla scheda giocatore
                    await page.goto(f"https://www.fitp.it{g_url}", wait_until="domcontentloaded")
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    
                    risultati.append({
                        "torneo": full_url,
                        "nome": nome.strip()
                    })
                    logger.info(f"Estratto: {nome.strip()}")
                    
                # Ritorna alla pagina principale del torneo
                await page.goto(full_url, wait_until="networkidle")
        
        # Salvataggio
        with open("Risultati_Iscrizioni.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        logger.info("Bot terminato correttamente.")

if __name__ == "__main__":
    asyncio.run(run_bot())
