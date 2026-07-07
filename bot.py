import asyncio
import json
import logging
from playwright.async_api import async_playwright

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

async def run_bot():
    logger.info("--- Avvio Bot: Estrazione Iscrizioni Aperte con Scheda Giocatore ---")
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
        
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # Caricamento risultati
        while await page.locator("#btn-loadMore").is_visible():
            await page.click("#btn-loadMore")
            await asyncio.sleep(2)
            
        # Troviamo tutti i link dei tornei
        links = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in links]))
        logger.info(f"Trovati {len(urls)} tornei.")
        
        risultati = []
        for url_path in urls:
            full_url = f"https://www.fitp.it{url_path}"
            logger.info(f"Analizzo Torneo: {full_url}")
            
            try:
                await page.goto(full_url, wait_until="networkidle")
                
                # Nome Torneo
                nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").first.text_content()
                
                # Estraiamo i link dei giocatori che si trovano nel container con id 'players'
                # Il selettore è 'a[href*="Pagina-Giocatore"]' basato sui tuoi screenshot
                giocatori_links = await page.locator("a[href*='Pagina-Giocatore']").all()
                lista_nomi = []
                
                for link_giocatore in giocatori_links:
                    url_giocatore = await link_giocatore.get_attribute("href")
                    # Navighiamo nella scheda giocatore per prendere il nome pulito
                    await page.goto(f"https://www.fitp.it{url_giocatore}")
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    lista_nomi.append(nome.strip())
                    # Torniamo indietro al torneo
                    await page.go_back()
                
                risultati.append({
                    "torneo": nome_torneo.strip(),
                    "iscritti": lista_nomi
                })
                
            except Exception as e:
                logger.error(f"Errore durante analisi torneo: {e}")
        
        with open("Iscrizioni_Aperte_Dettaglio.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        logger.info("--- Salvataggio completato: Iscrizioni_Aperte_Dettaglio.json ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
