import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Scraper Definitivo - Pulizia Nomi e Titoli ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # 1. Navigazione
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        print("--- [INFO] Applicazione filtri...")
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
        
        # Recupero Tornei
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        print(f"--- [INFO] Trovati {len(urls)} tornei. Inizio analisi... ---")
        
        data_giov = []
        data_open = []
        
        # 2. Estrazione
        for url in urls:
            try:
                full_url = f"https://www.fitp.it{url}"
                await page.goto(full_url, wait_until="domcontentloaded")
                await page.wait_for_selector(".cc-section-participants", timeout=15000)
                
                # Nome Torneo specifico
                nome_torneo = await page.evaluate("""() => {
                    const el = document.querySelector('.cc-title-main') || document.querySelector('h1');
                    return el ? el.innerText.trim() : "Torneo Sconosciuto";
                }""")
                
                # Filtro Nomi Pulito (esclude ranking, date, scritte di sistema)
                nomi = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('.cc-content-value'))
                                .map(el => el.innerText.trim())
                                .filter(text => {
                                    if (text.length < 3) return false;
                                    if (text.includes('/')) return false;
                                    if (text.toLowerCase().includes('pdf') || text.toLowerCase().includes('scarica')) return false;
                                    if (text.includes('€')) return false;
                                    if (/^[\\d.,\\s]+$/.test(text)) return false; // Elimina i ranking (es. 4.5)
                                    return true;
                                });
                }""")
                
                entry = {"torneo": nome_torneo, "iscritti": sorted(list(set(nomi)))}
                
                if any(kw in nome_torneo.lower() for kw in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                    data_giov.append(entry)
                else:
                    data_open.append(entry)
                    
                print(f"--- [OK] Estratti {len(nomi)} iscritti da: {nome_torneo[:30]}... ---")
                    
            except Exception as e:
                print(f"--- [ERRORE] su {url}: {e} ---")
                continue

        # 3. Salvataggio
        with open("Iscritti_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_open, f, ensure_ascii=False, indent=4)
                
        await browser.close()
        print("--- [END] Processo completato. File generati! ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
