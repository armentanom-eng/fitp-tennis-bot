import asyncio
import json
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # --- 1. Navigazione e Filtri ---
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        logger.info("-> Impostazione Filtri...")
        # Apri menu Stato e seleziona "Iscrizioni Aperte"
        await page.click('button[data-id="select_status"]')
        await page.locator('span.filter-option:has-text("Iscrizioni Aperte")').click()
        
        # Apri menu Regione e seleziona "Lazio"
        await page.click('button[data-id="id_regioneSearch"]')
        await page.locator('span.filter-option:has-text("Lazio")').click()
        
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # --- 2. Raccolta Tornei ---
        links = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in links]))
        
        logger.info(f"Trovati {len(urls)} tornei.")
        risultati = []

        for i, url in enumerate(urls, 1):
            full_url = f"https://www.fitp.it{url}"
            logger.info(f"[{i}/{len(urls)}] ACCESSO TORNEO: {full_url}")
            await page.goto(full_url, wait_until="networkidle")
            
            # --- 3. Ciclo Categorie ---
            # Clicchiamo su ogni tab disponibile (es. Singolare, Doppio, etc)
            tabs = await page.locator("a[data-toggle='tab']").all()
            for tab in tabs:
                tab_name = await tab.text_content()
                await tab.click()
                await asyncio.sleep(1) # Attesa per caricamento tabella partecipanti
                
                # --- 4. Estrazione Giocatori ---
                # Trova tutti i link dentro la riga dei partecipanti (id="players")
                giocatori = await page.locator("#players a[href*='Pagina-Giocatore']").all()
                for j, g_link in enumerate(giocatori, 1):
                    href = await g_link.get_attribute("href")
                    g_url = f"https://www.fitp.it{href}"
                    
                    # Entra nella scheda giocatore
                    await page.goto(g_url, wait_until="networkidle")
                    # Preleva il nome dallo span indicato
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    logger.info(f"    -> Giocatore [{j}]: {nome.strip()} (Link: {g_url})")
                    risultati.append({"torneo": full_url, "categoria": tab_name, "nome": nome.strip()})
                    await page.go_back()
                    
        with open("Risultati_Finali.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        logger.info("Estrazione completata con successo.")

if __name__ == "__main__":
    asyncio.run(run_bot())
