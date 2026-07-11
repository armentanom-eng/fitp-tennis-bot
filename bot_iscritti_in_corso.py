import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio estrazione totale ---")
    
    # Lista che conterrà TUTTI i tornei estratti prima di dividerli
    tutti_i_tornei = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(20000)
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        
        # Filtri
        print("-> Impostazione Filtri...")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In corso").click()
        await asyncio.sleep(2)
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await asyncio.sleep(2)
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await asyncio.sleep(2)
        await asyncio.sleep(5)
        
        # Espansione
        while True:
            btn = page.locator("button#btn-loadMore")
            if await btn.is_visible():
                await btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(2)
            else:
                break
        
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        
        print(f"--- Trovati {len(urls)} tornei. Inizio estrazione dati grezzi. ---")
        
        # 1. ESTRAZIONE: Qui ci limitiamo a raccogliere tutto senza decidere ancora la categoria
        for url in urls:
            print(f"-> Analizzo torneo: {url[-10:]}")
            try:
                await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                if await page.locator("text=non e' al momento disponibile").is_visible(): continue
                
                count = await page.locator("text=Dettaglio >").count()
                for i in range(count):
                    await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                    btn = page.locator("text=Dettaglio >").nth(i)
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await page.wait_for_load_state("domcontentloaded")
                        
                        cat = await page.locator("h1.cc-title-main").first.text_content()
                        tab = await page.locator("span#spn-tournament-description").text_content() if await page.locator("span#spn-tournament-description").count() > 0 else ""
                        giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                        
                        # Salviamo nel calderone comune
                        tutti_i_tornei.append({
                            "torneo": url, 
                            "categoria": cat.strip() if cat else "", 
                            "tabellone": tab.strip() if tab else "", 
                            "iscritti": [g.strip() for g in giocatori]
                        })
            except Exception as e:
                print(f"    ! Errore su {url[-10:]}: {e}")
        
        await browser.close()

    # 2. CLASSIFICAZIONE: Ora dividiamo i dati in due liste distinte
    print("--- Estrazione terminata. Divisione in corso... ---")
    dati_giovanili = {"tornei": []}
    dati_open = {"tornei": []}
    
    keywords = ["under", "u10", "u12", "u14", "u16", "u18", "giovanile", "junior"]
    
    for torneo in tutti_i_tornei:
        testo_check = (torneo["categoria"] + " " + torneo["tabellone"]).lower()
        
        # Se trova le parole chiave, va nei Giovanili
        if any(k in testo_check for k in keywords):
            dati_giovanili["tornei"].append(torneo)
        # Se NON le trova, va negli Open
        else:
            dati_open["tornei"].append(torneo)
            
    # 3. SCRITTURA: Due file separati, nessun rischio di mischiare
    with open("Iscritti_Giovanili_In_Corso.json", "w", encoding="utf-8") as f: 
        json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        print(f"-> Scritto file GIOVANILI: {len(dati_giovanili['tornei'])} tornei.")
        
    with open("Iscritti_Open_In_Corso.json", "w", encoding="utf-8") as f: 
        json.dump(dati_open, f, ensure_ascii=False, indent=4)
        print(f"-> Scritto file OPEN: {len(dati_open['tornei'])} tornei.")

    print("--- [END] Processo completato correttamente. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
