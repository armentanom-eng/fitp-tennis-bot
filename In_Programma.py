import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio estrazione totale ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(15000)
        
        # Navigazione iniziale
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        await page.click('button[data-id="select_status"]')
        await page.locator('span:text-is("In programma")').last.click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.locator('span:text-is("Roma")').last.click()      
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Recupero lista URL tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. Inizio ciclo totale. ---")
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            print(f"--- Analizzo torneo: {url[-10:]} ---")
            try:
                await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                
                # Controllo pop-up errore
                if await page.locator("text=non e' al momento disponibile").is_visible():
                    print("    -> Torneo non disponibile, salto.")
                    continue
                
                # Conta quanti bottoni 'Dettaglio' ci sono
                count = await page.locator("text=Dettaglio >").count()
                
                for i in range(count):
                    # Ricarichiamo la pagina principale del torneo ad ogni giro per resettare lo stato
                    await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                    
                    btn = page.locator("text=Dettaglio >").nth(i)
                    if await btn.is_visible():
                        try:
                            await btn.click(force=True)
                            await page.wait_for_load_state("domcontentloaded")
                            
                            categoria = await page.locator("h1.cc-title-main").first.text_content()
                            giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                            
                            entry = {"torneo": url, "categoria": categoria.strip(), "iscritti": [g.strip() for g in giocatori]}
                            if any(x in categoria.lower() for x in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                                dati_giovanili["tornei"].append(entry)
                            else:
                                dati_open["tornei"].append(entry)
                            
                            print(f"    -> Estratti {len(giocatori)} iscritti da: {categoria.strip()}")
                        except Exception as e:
                            print(f"    ! Errore cliccando il dettaglio {i}: {e}")
                            
            except Exception as e:
                print(f"    ! Errore critico nel torneo {url[-10:]}: {e}")
        
        # Salvataggio finale
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
