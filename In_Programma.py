import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Scraper Definitivo - Nomi Puliti ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # 1. Navigazione e Filtri
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
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
        
        # Recupera URL tornei
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        data_giov = []
        data_open = []
        
        # 2. Ciclo di estrazione
        for url in urls:
            try:
                full_url = f"https://www.fitp.it{url}"
                await page.goto(full_url, wait_until="domcontentloaded")
                await page.wait_for_selector(".cc-section-participants", timeout=15000)
                
                # ESTRAZIONE TITOLO PRECISA
                nome_torneo_element = await page.query_selector("h1.cc-title-main")
                nome_torneo = await nome_torneo_element.inner_text() if nome_torneo_element else "Torneo Sconosciuto"
                
                # ESTRAZIONE AGGRESSIVA NOMI
                # Prende solo stringhe tutte maiuscole (esclude date, prezzi, "Scarica pdf")
                nomi = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('.cc-content-value'))
                                .map(el => el.innerText.trim())
                                .filter(text => text.length > 3 
                                                && text === text.toUpperCase() 
                                                && !text.includes('PDF') 
                                                && !text.includes('€')
                                                && !text.includes('/'));
                }""")
                
                entry = {
                    "torneo": nome_torneo.strip(),
                    "iscritti": sorted(list(set(nomi)))
                }
                
                # Separazione Giovanili vs Open
                if any(kw in nome_torneo.lower() for kw in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                    data_giov.append(entry)
                else:
                    data_open.append(entry)
                    
                print(f"--- [OK] Analizzato: {nome_torneo.strip()} ---")
                    
            except Exception as e:
                print(f"--- [INFO] Saltato torneo {url}: {e} ---")
                continue

        # 3. Salvataggio JSON
        with open("Iscritti_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_open, f, ensure_ascii=False, indent=4)
                
        await browser.close()
        print("--- [END] Processo completato: File JSON pronti ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
