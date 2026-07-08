import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio Bot Anti-Blocco ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        await page.click('button[data-id="select_status"]')
        await page.locator('span:text-is("In programma")').last.click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.locator('span:text-is("Roma")').last.click()      
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            print(f"--- Analizzo: {url[-10:]} ---")
            await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
            
            # PROTEZIONE ANTI-POPUP
            # Se trova il banner di errore, lo chiude (cliccando la X) o torna indietro
            if await page.locator("text=non e' al momento disponibile").count() > 0:
                print("    -> Pagina errore rilevata, salto.")
                continue

            tutti_i_bottoni = page.locator("text=Dettaglio >")
            # Filtriamo solo quelli che sono DAVVERO visibili
            bottoni_visibili = [tutti_i_bottoni.nth(i) for i in range(await tutti_i_bottoni.count()) if await tutti_i_bottoni.nth(i).is_visible()]
            
            for btn in bottoni_visibili:
                try:
                    await btn.click(force=True)
                    await page.wait_for_load_state("networkidle")
                    
                    categoria = await page.locator("h1.cc-title-main").first.text_content()
                    giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                    
                    entry = {"torneo": url, "categoria": categoria.strip(), "iscritti": [g.strip() for g in giocatori]}
                    
                    if any(x in categoria.lower() for x in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                        dati_giovanili["tornei"].append(entry)
                    else:
                        dati_open["tornei"].append(entry)
                    
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
                except Exception as e:
                    print(f"    ! Errore clic su bottone: {e}")
                    await page.goto(f"https://www.fitp.it{url}")
        
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
