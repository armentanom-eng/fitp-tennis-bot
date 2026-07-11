import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio estrazione ISCRITTI (In Corso) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(60000) # Timeout esteso
        
        # 1. Navigazione iniziale
        print("-> Navigazione verso il sito FITP...")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        
        # 2. Filtri (Uniformati al codice funzionante)
        print("-> Impostazione Filtri: In corso, Lazio, Roma")
        
        # Stato
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In corso").click()
        await asyncio.sleep(2)
        
        # Regione
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await asyncio.sleep(2)
        
        # Provincia
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await asyncio.sleep(2)
        
        # Attesa per caricamento risultati filtrati
        await asyncio.sleep(5)
        
        # 3. Espansione lista
        print("-> Caricamento lista tornei...")
        while True:
            btn_load_more = page.locator("button#btn-loadMore")
            if await btn_load_more.is_visible():
                print("    -> Trovato 'Carica altri', espando...")
                await btn_load_more.click()
                await asyncio.sleep(3)
            else:
                break
        
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. Inizio analisi dettagliata. ---")
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            print(f"-> Analisi torneo: {full_url[-10:]}")
            await page.goto(full_url, wait_until="domcontentloaded")
            
            # Attendiamo che siano visibili i pulsanti dettaglio
            count = await page.locator("text=Dettaglio >").count()
            print(f"    -> Trovati {count} tabelloni.")
            
            for i in range(count):
                btn = page.locator("text=Dettaglio >").nth(i)
                if await btn.is_visible():
                    try:
                        await btn.click(force=True)
                        await page.wait_for_load_state("domcontentloaded")
                        await asyncio.sleep(2)
                        
                        # Estrazione Dati
                        cat_el = page.locator("h1.cc-title-main").first
                        categoria = await cat_el.text_content() if await cat_el.count() > 0 else "N/A"
                        
                        tabellone_el = page.locator("span#spn-tournament-description")
                        tabellone = await tabellone_el.text_content() if await tabellone_el.count() > 0 else "N/A"
                        
                        giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                        
                        entry = {
                            "torneo": url, 
                            "categoria": categoria.strip(), 
                            "tabellone": tabellone.strip(), 
                            "iscritti": [g.strip() for g in giocatori]
                        }
                        
                        if any(x in categoria.lower() for x in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                            dati_giovanili["tornei"].append(entry)
                        else:
                            dati_open["tornei"].append(entry)
                        
                        print(f"      -> Estratto tabellone: {tabellone.strip()} ({len(giocatori)} iscritti)")
                        
                        # Ottimizzazione: torniamo indietro invece di ricaricare tutto
                        await page.go_back()
                        await page.wait_for_selector("text=Dettaglio >")
                        
                    except Exception as e:
                        print(f"      ! Errore estrazione dettaglio {i}: {e}")
                        await page.goto(full_url, wait_until="domcontentloaded")

        # 4. Salvataggio finale
        print("-> Salvataggio file JSON...")
        with open("Iscritti_Giovanili_In_Corso.json", "w", encoding="utf-8") as f: 
            json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Corso.json", "w", encoding="utf-8") as f: 
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato con successo. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
