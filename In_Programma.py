import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio bot In_Programma ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("--- Navigazione portale FITP ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        
        # --- FILTRI ---
        print("--- Applicazione filtri ---")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # Caricamento totale lista
        print("--- Caricamento totale lista tornei (espansione...) ---")
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await asyncio.sleep(1)
            print("    -> Caricati altri tornei...")
            
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        print(f"--- Trovati {len(urls)} tornei. Inizio analisi ---")
        
        dati_giovanili = {"tornei": []}
        dati_open = {"tornei": []}
        
        for idx, url in enumerate(urls):
            try:
                await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                categoria = await page.locator("h1.cc-title-main").first.text_content()
                
                giocatori_locators = page.locator("a[href*='Pagina-Giocatore']")
                if await giocatori_locators.count() == 0:
                    continue 

                giocatori = [await el.text_content() for el in await giocatori_locators.all()]
                entry = {"torneo": url, "categoria": categoria.strip(), "dati": [g.strip() for g in giocatori]}
                
                if any(x in categoria for x in ["Under", "Giovanile", "U10", "U11", "U12", "U14", "U16"]):
                    dati_giovanili["tornei"].append(entry)
                else:
                    dati_open["tornei"].append(entry)
                
                print(f"    [{idx+1}/{len(urls)}] Analizzato: {categoria.strip()}")
                
                # Salvataggio "salvavita" durante il ciclo
                if idx % 5 == 0: 
                    with open("Partite_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
                        json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
                    with open("Partite_Open_In_Programa.json", "w", encoding="utf-8") as f:
                        json.dump(dati_open, f, ensure_ascii=False, indent=4)
                        
            except Exception as e:
                print(f"    ! Errore su torneo {url}: {e}")
                continue 
        
        # Salvataggio finale
        with open("Partite_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Partite_Open_In_Programa.json", "w", encoding="utf-8") as f:
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato correttamente. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
