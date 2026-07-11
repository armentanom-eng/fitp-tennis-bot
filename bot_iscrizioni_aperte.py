import asyncio
import json
from playwright.async_api import async_playwright

# Mappa delle categorie con i nuovi nomi file richiesti
CATEGORIES = {
    "t_giovanili": "Iscritti_Giovanili_In_Corso.json", 
    "t_affiliati": "Iscritti_Open_In_Corso.json"
}

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

async def run_bot():
    print("--- [START] Avvio estrazione WEB (Filtro: 'Iscrizioni aperte') ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(30000)
        
        # Iteriamo sulle categorie
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Elaborazione categoria: {cat_id}")
            dati_categoria = {"tornei": []}
            
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            
            # --- 1. FILTRI BASE ---
            # Modificato filtro stato in "Iscrizioni aperte"
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
            await asyncio.sleep(2)
            
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(2)
            
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(2)
            
            # --- 2. FILTRO CATEGORIA ---
            print(f"-> Clicco filtro categoria: {cat_id}")
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            # Attendiamo il ricaricamento della lista
            await asyncio.sleep(4) 
            
            # --- 3. ESPANSIONE LISTA ---
            while True:
                btn_load_more = page.locator("button#btn-loadMore")
                if await btn_load_more.is_visible():
                    await btn_load_more.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(2)
                else:
                    break
            
            # --- 4. ESTRAZIONE ---
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            urls = list(set([await loc.get_attribute("href") for loc in locators]))
            print(f"-> Trovati {len(urls)} tornei. Estrazione...")
            
            for url in urls:
                try:
                    await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                    if await page.locator("text=non e' al momento disponibile").is_visible(): continue
                    
                    count = await page.locator("text=Dettaglio >").count()
                    for i in range(count):
                        # Torniamo alla pagina del torneo per ogni bottone
                        await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                        btn = page.locator("text=Dettaglio >").nth(i)
                        
                        if await btn.is_visible():
                            await btn.click(force=True)
                            await page.wait_for_load_state("domcontentloaded")
                            
                            categoria = await page.locator("h1.cc-title-main").first.text_content()
                            tabellone_el = page.locator("span#spn-tournament-description")
                            tabellone = await tabellone_el.text_content() if await tabellone_el.count() > 0 else "N/A"
                            giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                            
                            dati_categoria["tornei"].append({
                                "torneo": url, 
                                "categoria": categoria.strip() if categoria else "", 
                                "tabellone": tabellone.strip(), 
                                "iscritti": [g.strip() for g in giocatori]
                            })
                            print(f"    -> Estratto: {tabellone.strip()}")
                except Exception as e:
                    print(f"    ! Errore su {url[-10:]}: {e}")
            
            # --- 5. SALVATAGGIO ---
            with open(filename, "w", encoding="utf-8") as f: 
                json.dump(dati_categoria, f, ensure_ascii=False, indent=4)
            print(f"-> SALVATO: {filename}")
            
        await browser.close()
        print("--- [END] Processo completato. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
