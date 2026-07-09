import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio estrazione ISCRITTI (Tornei in Corso - Lazio/Roma) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(60000)
        
        print("-> Navigazione verso il portale FITP...")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # 1. FILTRO STATO
        print("-> Impostazione filtro STATO: 'In corso'...")
        await page.click('button[data-id="select_status"]')
        await page.locator('div.dropdown-menu.open a:has-text("In corso")').first.click(force=True)
        await asyncio.sleep(2)
        
        # 2. FILTRO REGIONE (Lazio)
        print("-> Impostazione filtro REGIONE: 'Lazio'...")
        await page.click('button[data-id="id_regioneSearch"]')
        # Usiamo .first per evitare violazioni di strict mode
        await page.locator('div.dropdown-menu.open').get_by_role("option", name="Lazio").first.click(force=True)
        await asyncio.sleep(3) # Attesa necessaria per caricare le province
        
        # 3. FILTRO PROVINCIA (Roma)
        print("-> Impostazione filtro PROVINCIA: 'Roma'...")
        await page.click('button[data-id="id_provinciaSearch"]')
        # Attesa visibilità dell'opzione specifica
        roma_opt = page.locator('div.dropdown-menu.open li a:has-text("Roma")').last
        await roma_opt.wait_for(state="visible")
        await roma_opt.click(force=True)
        
        # Conferma filtri
        await page.keyboard.press("Enter")
        print("-> Filtri applicati. Attesa caricamento risultati...")
        await asyncio.sleep(5)
        
        # --- ESPANSIONE LISTA ---
        print("--- Caricamento totale lista tornei... ---")
        while True:
            btn_load_more = page.locator("button#btn-loadMore")
            if await btn_load_more.is_visible():
                print("    -> Trovato 'Carica altri', espando...")
                await btn_load_more.click()
                await asyncio.sleep(3)
            else:
                print("    -> Lista completa caricata.")
                break
        
        # Recupero URL tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. Inizio estrazione dettagli. ---")
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for index, url in enumerate(urls):
            full_url = f"https://www.fitp.it{url}"
            print(f"[{index+1}/{len(urls)}] Analizzo: {url[-10:]}")
            try:
                await page.goto(full_url, wait_until="domcontentloaded")
                nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                
                count = await page.locator("text=Dettaglio >").count()
                for i in range(count):
                    # Ricarichiamo la pagina per resettare lo stato dei clic
                    await page.goto(full_url, wait_until="domcontentloaded")
                    btn = page.locator("text=Dettaglio >").nth(i)
                    
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await page.wait_for_load_state("domcontentloaded")
                        
                        categoria = await page.locator("h1.cc-title-main").first.text_content()
                        tabellone = await page.locator("span#spn-tournament-description").text_content() or "N/A"
                        giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                        
                        entry = {
                            "nomeTorneo": nome_torneo.strip(),
                            "categoria": categoria.strip(), 
                            "tabellone": tabellone.strip(), 
                            "iscritti": [g.strip() for g in giocatori]
                        }
                        
                        cat_lower = categoria.lower()
                        if any(x in cat_lower for x in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                            dati_giovanili["tornei"].append(entry)
                        else:
                            dati_open["tornei"].append(entry)
            except Exception as e:
                print(f"    ! Errore su {url[-10:]}: {e}")
        
        print("-> Salvataggio file JSON...")
        with open("Iscritti_Giovanili_In_Corso.json", "w", encoding="utf-8") as f:
            json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Corso.json", "w", encoding="utf-8") as f:
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        print("--- [END] Processo completato. ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
