import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Scraper Definitivo - Separazione Giovanili/Open ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Navigazione
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        for filter_btn, option_text in [
            ('button[data-id="select_status"]', "In programma"),
            ('button[data-id="id_regioneSearch"]', "Lazio"),
            ('button[data-id="id_provinciaSearch"]', "Roma")
        ]:
            await page.locator(filter_btn).click()
            await page.locator(f'span:text-is("{option_text}")').last.click()
            await asyncio.sleep(1)
            
        await page.locator('#btn-search').click()
        await asyncio.sleep(5)
        
        # Recupera URL
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        data_giov = []
        data_open = []
        
        for url in urls:
            try:
                full_url = f"https://www.fitp.it{url}"
                await page.goto(full_url, wait_until="domcontentloaded")
                await page.wait_for_selector(".cc-section-participants", timeout=10000)
                
                nome_torneo = await page.locator("h1.cc-title-main").first.text_content()
                
                # ESTRAZIONE E FILTRO
                raw_data = await page.locator(".cc-content-value").all_text_contents()
                partecipanti = []
                for item in raw_data:
                    testo = item.strip()
                    if (len(testo) > 3 and 
                        "pdf" not in testo.lower() and 
                        "scarica" not in testo.lower() and 
                        "documento" not in testo.lower() and 
                        "disponibile" not in testo.lower() and 
                        "€" not in testo and 
                        "/" not in testo and
                        "singolare" not in testo.lower()):
                        partecipanti.append(testo)
                
                entry = {
                    "torneo": nome_torneo.strip(),
                    "iscritti": sorted(list(set(partecipanti)))
                }
                
                # Logica di separazione (Giovanile vs Open)
                if any(kw in nome_torneo.lower() for kw in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                    data_giov.append(entry)
                else:
                    data_open.append(entry)
                    
            except Exception as e:
                print(f"--- [INFO] Saltato torneo {url}: {e} ---")
                continue

        # Salvataggio file
        with open("Iscritti_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_open, f, ensure_ascii=False, indent=4)
                
        await browser.close()
        print("--- [END] Processo completato: File JSON generati ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
