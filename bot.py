import asyncio
import json
import logging
from playwright.async_api import async_playwright

# Configurazione logging per tracciare il percorso
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Accesso iniziale
        logger.info("Navigazione su portale tornei...")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # 2. Impostazione Filtri con XPATH (più robusto per bootstrap-select)
        logger.info("Impostazione filtri: Iscrizioni Aperte e Lazio...")
        
        await page.click('button[data-id="select_status"]')
        await asyncio.sleep(1)
        await page.locator("//div[contains(@class, 'dropdown-menu')]//span[contains(text(), 'Iscrizioni Aperte')]").click()
        
        await page.click('button[data-id="id_regioneSearch"]')
        await asyncio.sleep(1)
        await page.locator("//div[contains(@class, 'dropdown-menu')]//span[contains(text(), 'Lazio')]").click()
        
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # 3. Raccolta Tornei
        logger.info("Ricerca tornei nel Lazio...")
        links = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in links]))
        logger.info(f"Trovati {len(urls)} tornei.")
        
        risultati = []

        # 4. Ciclo Tornei
        for i, url in enumerate(urls, 1):
            full_url = f"https://www.fitp.it{url}"
            logger.info(f"[{i}/{len(urls)}] ACCESSO TORNEO: {full_url}")
            await page.goto(full_url, wait_until="networkidle")
            
            # Ciclo Categorie (Tab)
            tabs = await page.locator("a[data-toggle='tab']").all()
            for tab in tabs:
                tab_name = await tab.text_content()
                logger.info(f"  -> Analisi Categoria: {tab_name.strip()}")
                await tab.click()
                await asyncio.sleep(2) # Attesa caricamento lista giocatori
                
                # 5. Estrazione Giocatori tramite Scheda
                giocatori = await page.locator("#players a[href*='Pagina-Giocatore']").all()
                for j, g_link in enumerate(giocatori, 1):
                    href = await g_link.get_attribute("href")
                    g_url = f"https://www.fitp.it{href}"
                    
                    try:
                        await page.goto(g_url, wait_until="networkidle")
                        nome = await page.locator("span#spn-tournament-description").text_content()
                        logger.info(f"    -> Giocatore [{j}/{len(giocatori)}]: {nome.strip()}")
                        risultati.append({
                            "torneo": full_url, 
                            "categoria": tab_name.strip(), 
                            "nome": nome.strip()
                        })
                        await page.go_back()
                    except Exception as e:
                        logger.error(f"Errore su giocatore {g_url}: {e}")
                        await page.go_back()
                    
        # 6. Salvataggio
        with open("Risultati_Iscrizioni.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
            
        logger.info("Estrazione completata. File salvato: Risultati_Iscrizioni.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
