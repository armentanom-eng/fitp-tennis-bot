import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio estrazione divisa per categoria ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(20000)
        
        # 1. Navigazione e Filtri
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
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
        
        # 2. Espansione Lista
        while True:
            btn_load_more = page.locator("button#btn-loadMore")
            if await btn_load_more.is_visible():
                await btn_load_more.click()
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(2)
            else:
                break
        
        # 3. Raccolta URL
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        
        # 4. DIVISIONE: Creiamo due liste separate PRIMA di estrarre i dati
        lista_giovanili = []
        lista_open = []
        keywords = ["under", "u10", "u12", "u14", "u16", "u18", "giovanile", "junior"]
        
        print(f"--- Trovati {len(urls)} tornei. Classifico... ---")
        
        # Questo ciclo serve SOLO a capire di che categoria è il torneo (senza estrarre ancora gli iscritti)
        for url in urls:
            # Per sicurezza, andiamo sulla pagina per leggere il titolo e capire la categoria
            await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
            cat = await page.locator("h1.cc-title-main").first.text_content()
            tab = await page.locator("span#spn-tournament-description").text_content() if await page.locator("span#spn-tournament-description").count() > 0 else ""
            
            testo_check = (str(cat) + " " + str(tab)).lower()
            
            if any(k in testo_check for k in keywords):
                lista_giovanili.append(url)
            else:
                lista_open.append(url)

        # 5. ESTRAZIONE E SALVATAGGIO SEPARATO
        dati_giovanili = {"tornei": []}
        dati_open = {"tornei": []}

        # Elabora solo i GIOVANILI
        print(f"--- Estraggo {len(lista_giovanili)} tornei GIOVANILI ---")
        for url in lista_giovanili:
            dati_giovanili["tornei"].extend(await estrai_dati_torneo(page, url))
        
        with open("Iscritti_Giovanili_In_Corso.json", "w", encoding="utf-8") as f: 
            json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)

        # Elabora solo gli OPEN
        print(f"--- Estraggo {len(lista_open)} tornei OPEN ---")
        for url in lista_open:
            dati_open["tornei"].extend(await estrai_dati_torneo(page, url))
            
        with open("Iscritti_Open_In_Corso.json", "w", encoding="utf-8") as f: 
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato correttamente. ---")

# Funzione helper per non ripetere il codice
async def estrai_dati_torneo(page, url):
    risultati = []
    await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
    count = await page.locator("text=Dettaglio >").count()
    for i in range(count):
        await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
        btn = page.locator("text=Dettaglio >").nth(i)
        if await btn.is_visible():
            await btn.click(force=True)
            await page.wait_for_load_state("domcontentloaded")
            cat = await page.locator("h1.cc-title-main").first.text_content()
            tab = await page.locator("span#spn-tournament-description").text_content()
            giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
            risultati.append({
                "torneo": url, "categoria": cat.strip(), "tabellone": tab.strip(), "iscritti": [g.strip() for g in giocatori]
            })
    return risultati

if __name__ == "__main__":
    asyncio.run(run_bot())
