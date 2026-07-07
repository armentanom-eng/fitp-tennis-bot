import asyncio
import json
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri (logica confermata)
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # Estrazione URL tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        
        risultati = []
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            await page.goto(full_url, wait_until="networkidle")
            
            # Identifichiamo quanti blocchi categoria ci sono (es. Singolare Femminile, Maschile)
            # Usiamo il selettore specifico del bottone Dettaglio presente in ogni box
            dettagli = page.locator("a:has-text('Dettaglio >')")
            count = await dettagli.count()
            
            for i in range(count):
                # Clicchiamo il dettaglio della i-esima categoria
                await dettagli.nth(i).click()
                await page.wait_for_load_state("networkidle")
                
                # Ora siamo dentro la lista partecipanti della specifica categoria
                giocatori = await page.locator("a[href*='Pagina-Giocatore']").all()
                for g_link in giocatori:
                    g_url = await g_link.get_attribute("href")
                    await page.goto(f"https://www.fitp.it{g_url}", wait_until="domcontentloaded")
                    
                    # Nome giocatore preso dallo span corretto (come da tua foto)
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    risultati.append({"torneo": full_url, "nome": nome.strip()})
                    logger.info(f"Estratto: {nome.strip()}")
                    
                    # Ritorno alla lista categoria usando il tasto 'Torna ai risultati' 
                    # o il link breadcrumb (che è sempre presente in pagina scheda giocatore)
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
                
                # Ritorno alla pagina principale del torneo per cliccare la categoria successiva
                await page.goto(full_url, wait_until="networkidle")
                # Ricalcoliamo i dettagli dopo il ritorno alla pagina principale
                dettagli = page.locator("a:has-text('Dettaglio >')")
        
        with open("Risultati_Iscrizioni.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
