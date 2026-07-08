import asyncio
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Scraper Definitivo ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Emuliamo un utente reale
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # 1. Navigazione
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
        
        # Recupero URL
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        # 2. Ciclo Tornei
        for url in urls:
            try:
                await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                await asyncio.sleep(3) # Pausa fissa per caricamento dati
                
                nome_torneo = await page.locator("h1.cc-title-main").first.text_content()
                
                # Prendiamo TUTTO quello che c'è nelle celle dei partecipanti
                raw_data = await page.locator(".cc-content-value").all_text_contents()
                
                # PULIZIA FEROCE: teniamo solo stringhe lunghe, niente date, niente euro, niente info tecniche
                partecipanti = []
                for item in raw_data:
                    clean = item.strip()
                    # Filtri per escludere date (xx/xx/xxxx), prezzi, info tecniche
                    if len(clean) > 4 and "/" not in clean and "€" not in clean and "Si" != clean and "No" != clean:
                        if clean not in partecipanti: # Evita duplicati
                            partecipanti.append(clean)
                
                # Output pulito
                print(f"\nTORNEO: {nome_torneo.strip()}")
                print("PARTECIPANTI:")
                for p in partecipanti:
                    print(f"- {p}")
                print("-" * 40)
                    
            except Exception:
                continue
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
