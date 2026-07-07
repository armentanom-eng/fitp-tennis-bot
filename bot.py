import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Messo False per debuggare meglio
        page = await browser.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri (con la logica che sappiamo funzionare)
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # Estrai link tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        
        risultati = []
        
        for url in urls:
            await page.goto(f"https://www.fitp.it{url}")
            
            # 1. Trova tutti i box "Dettaglio >"
            # Cerchiamo tutti i link che contengono "Dettaglio"
            dettaglio_links = await page.locator("a:has-text('Dettaglio >')").all()
            
            for i in range(len(dettaglio_links)):
                # Dobbiamo ricaricare la lista ad ogni giro perché navighiamo indietro
                links = await page.locator("a:has-text('Dettaglio >')").all()
                await links[i].click()
                await page.wait_for_load_state("networkidle")
                
                # 2. Ora siamo nella lista partecipanti della singola categoria
                # Estraiamo i link dei giocatori
                giocatori = await page.locator("a[href*='Pagina-Giocatore']").all()
                for g_link in giocatori:
                    g_url = await g_link.get_attribute("href")
                    
                    # Vai alla scheda giocatore
                    await page.goto(f"https://www.fitp.it{g_url}")
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    
                    risultati.append({"categoria_index": i, "nome": nome.strip()})
                    print(f"Estratto: {nome.strip()}")
                    await page.go_back()
                
                # Torna alla pagina principale del torneo per la prossima categoria
                await page.goto(f"https://www.fitp.it{url}")
        
        with open("Risultati_Finali.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
