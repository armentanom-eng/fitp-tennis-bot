import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        # [Inserisci qui la tua logica filtri che funziona]
        
        # 1. Recupero URL tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            await page.goto(full_url, wait_until="networkidle")
            
            # 2. CERCHIAMO I BOX DELLE CATEGORIE
            # Invece di cercare un bottone generico, cerchiamo il contenitore del box
            # che contiene la parola "Dettaglio"
            box_categorie = page.locator("div.cc-single-tournament") 
            count = await box_categorie.count()
            
            for i in range(count):
                print(f"Analizzo categoria {i+1} di {count}")
                
                # Clicchiamo "Dettaglio >" DENTRO il box i-esimo
                await box_categorie.nth(i).get_by_role("link", name="Dettaglio").click()
                await page.wait_for_load_state("networkidle")
                
                # 3. ESTRAZIONE GIOCATORI
                giocatori = await page.locator("a[href*='Pagina-Giocatore']").all()
                for g_link in giocatori:
                    g_url = await g_link.get_attribute("href")
                    await page.goto(f"https://www.fitp.it{g_url}")
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    print(f"Estratto: {nome}")
                    await page.go_back() # Torna alla lista della categoria
                
                # 4. TORNA AL TORNEO PRINCIPALE
                # Il "tasto che mi hai fatto vedere" (breadcrumb o link indietro)
                await page.get_by_text("Torna ai risultati").click() # O selettore simile del tasto
                await page.wait_for_load_state("networkidle")
                
                # Ricarichiamo il riferimento ai box dopo essere tornati indietro
                box_categorie = page.locator("div.cc-single-tournament")

        await browser.close()
