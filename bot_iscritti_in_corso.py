import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio estrazione ISCRITTI (Tutti i tornei) ---")
    async with async_playwright() as p:
        # headless=True per farlo girare in background, False per vedere cosa succede
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(60000)
        
        print("-> Navigazione verso il portale FITP...")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # 1. FILTRO STATO (In corso)
        print("-> Impostazione filtro STATO: 'In corso'...")
        await page.click('button[data-id="select_status"]')
        await page.locator('div.dropdown-menu.open a:has-text("In corso")').first.click(force=True)
        await asyncio.sleep(3)
        
        # Premi Invio per applicare
        await page.keyboard.press("Enter")
        print("-> Filtri applicati. Attesa caricamento risultati...")
        await asyncio.sleep(5)
        
        # ESPANSIONE LISTA
        print("--- Caricamento totale lista tornei... ---")
        while True:
            btn_load_more = page.locator("button#btn-loadMore")
            if await btn_load_more.is_visible():
                print("    -> Trovato 'Carica altri', espando...")
                await btn_load_more.click()
                await asyncio.sleep(4)
            else:
                print("    -> Lista completa caricata.")
                break
        
        # Recupero URL tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. Inizio estrazione iscritti... ---")
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for index, url in enumerate(urls):
            full_url = f"https://www.fitp.it{url}"
            try:
                await page.goto(full_url, wait_until="domcontentloaded")
                nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                print(f"[{index+1}/{len(urls)}] Analizzo: {nome_torneo.strip()}")
                
                count = await page.locator("text=Dettaglio >").count()
                for i in range(count):
                    # Ricarico per evitare conflitti tra i click
                    await page.goto(full_url, wait_until="domcontentloaded")
                    btn = page.locator("text=Dettaglio >").nth(i)
                    if await btn.is_visible():
                        await btn.click(force=True)
                        
                        # Aspettiamo che la tabella appaia a video
                        await page.wait_for_selector("table", timeout=10000)
                        await asyncio.sleep(2) 
                        
                        categoria = await page.locator("h1.cc-title-main").first.text_content()
                        tabellone = await page.locator("span#spn-tournament-description").text_content() or "N/A"
                        
                        # Lettura "a video" delle righe (tr)
                        rows = page.locator("table tbody tr")
                        count_rows = await rows.count()
                        giocatori = []
                        for r in range(count_rows):
                            nome = await rows.nth(r).text_content()
                            if nome and len(nome.strip()) > 3:
                                giocatori.append(nome.strip())
                        
                        entry = {
                            "nomeTorneo": f"{nome_torneo.strip()} - {tabellone.strip()}",
                            "categoria": categoria.strip(), 
                            "tabellone": tabellone.strip(), 
                            "iscritti": list(set(giocatori))
                        }
                        
                        # LOGICA GIOVANILI
                        if any(x in categoria.lower() for x in ["under", "u10", "u12", "u14", "u16", "u18", "giovanile", "junior"]):
                            dati_giovanili["tornei"].append(entry)
                        else:
                            dati_open["tornei"].append(entry)
                        print(f"    -> Estratto: {tabellone.strip()} con {len(list(set(giocatori)))} iscritti.")
            except Exception as e:
                print(f"    ! Errore su {url[-10:]}: {e}")
        
        print("-> Salvataggio file JSON...")
        with open("Iscritti_Giovanili_In_Corso.json", "w", encoding="utf-8") as f:
            json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Corso.json", "w", encoding="utf-8") as f:
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
