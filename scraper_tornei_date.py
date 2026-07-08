import asyncio
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

async def run_bot():
    print("--- Avvio estrazione tornei oggi e domani ---")
    oggi = datetime.now().date()
    domani = oggi + timedelta(days=1)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        await page.click('button[data-id="select_status"]')
        await page.locator('span:text-is("In programma")').last.click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Espansione lista
        while True:
            btn = page.locator("button#btn-loadMore")
            if await btn.is_visible(): 
                await btn.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
            else: 
                break
        
        # Recupero URL sicuri
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            try:
                await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
                
                # FILTRO DATA
                data_el = page.locator(".data-torneo").first
                if not await data_el.is_visible(): continue
                
                data_text = await data_el.text_content()
                data_torneo = datetime.strptime(data_text.strip(), "%d/%m/%Y").date()
                
                if data_torneo not in [oggi, domani]:
                    continue
                
                # Controllo presenza bottone Dettaglio
                dettaglio_btn = page.locator("text=Dettaglio >")
                if not await dettaglio_btn.first.is_visible():
                    continue

                count = await dettaglio_btn.count()
                for i in range(count):
                    # Ricarichiamo la pagina per ogni dettaglio se necessario, 
                    # ma verifichiamo sempre che il bottone sia cliccabile
                    btn = page.locator("text=Dettaglio >").nth(i)
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await page.wait_for_load_state("networkidle")
                        
                        categoria = await page.locator("h1.cc-title-main").first.text_content()
                        tabellone = await page.locator("span#spn-tournament-description").text_content()
                        giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                        
                        entry = {
                            "torneo": url, 
                            "categoria": categoria.strip() if categoria else "N/A", 
                            "tabellone": tabellone.strip() if tabellone else "N/A", 
                            "iscritti": [g.strip() for g in giocatori]
                        }
                        
                        if any(x in entry["categoria"].lower() for x in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                            dati_giovanili["tornei"].append(entry)
                        else:
                            dati_open["tornei"].append(entry)
                            
                        # Torniamo indietro alla pagina del torneo principale
                        await page.go_back()
                        await page.wait_for_load_state("networkidle")
            
            except Exception as e:
                print(f"Errore su {url}: {e}")
                continue 
        
        with open("Tornei_Date_Giovanili_In_Programma_PDF.json", "w", encoding="utf-8") as f: 
            json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Tornei_Date_Open_In_Programa_Pdf.json", "w", encoding="utf-8") as f: 
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
