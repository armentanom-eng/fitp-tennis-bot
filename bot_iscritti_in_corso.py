import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio estrazione totale (In Corso) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(20000)
        
        # Navigazione iniziale
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        
        # --- ARCHITETTURA FILTRI (TESTATA) ---
        print("-> Impostazione Filtri: In corso, Lazio, Roma")
        
        # 1. Stato: In corso
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In corso").click()
        await asyncio.sleep(2)
        
        # 2. Regione: Lazio
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await asyncio.sleep(2)
        
        # 3. Provincia: Roma
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await asyncio.sleep(2)
        
        # Pausa per permettere il caricamento dinamico dopo i filtri
        print("-> Filtri applicati, attendo caricamento risultati...")
        await asyncio.sleep(5)
        
        # --- CICLO ESPANSIONE LISTA (CARICA ALTRI) ---
        print("--- Caricamento totale lista tornei in corso... ---")
        while True:
            btn_load_more = page.locator("button#btn-loadMore")
            if await btn_load_more.is_visible():
                print("    -> Trovato 'Carica altri', espando...")
                await btn_load_more.click()
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(2) # Pausa di sicurezza
            else:
                print("    -> Lista completa caricata.")
                break
        
        # Recupero lista URL tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. Inizio ciclo totale. ---")
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            print(f"--- Analizzo torneo: {url[-10:]} ---")
            try:
                await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                
                if await page.locator("text=non e' al momento disponibile").is_visible():
                    print("    -> Torneo non disponibile, salto.")
                    continue
                
                count = await page.locator("text=Dettaglio >").count()
                
                for i in range(count):
                    # Ricarica pagina principale del torneo
                    await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                    
                    btn = page.locator("text=Dettaglio >").nth(i)
                    if await btn.is_visible():
                        try:
                            await btn.click(force=True)
                            await page.wait_for_load_state("domcontentloaded")
                            
                            # Estrazione Categoria Principale
                            categoria = await page.locator("h1.cc-title-main").first.text_content()
                            
                            # Estrazione precisa del Tabellone (es. Singolare Maschile)
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
                            
                            print(f"    -> Estratto: {tabellone.strip()} - {len(giocatori)} iscritti.")
                        except Exception as e:
                            print(f"    ! Errore cliccando il dettaglio {i}: {e}")
                            
            except Exception as e:
                print(f"    ! Errore critico nel torneo {url[-10:]}: {e}")
        
        # Salvataggio finale (Nomi aggiornati a "In_Corso")
        with open("Iscritti_Giovanili_In_Corso.json", "w", encoding="utf-8") as f: json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Corso.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
