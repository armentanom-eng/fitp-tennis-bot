import asyncio
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio Scraper Tornei FITP (Modalità Robusta) ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Navigazione
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri (stessa logica collaudata)
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
        
        for url in urls:
            try:
                full_url = f"https://www.fitp.it{url}"
                await page.goto(full_url, wait_until="domcontentloaded")
                
                # ESTRAZIONE DIRETTA (senza cliccare bottoni se non strettamente necessario)
                # Aspettiamo che il contenitore dei partecipanti sia caricato
                await page.wait_for_selector(".cc-section-participants", timeout=10000)
                
                nome_torneo = await page.locator("h1.cc-title-main").first.text_content()
                tutti_i_dati = await page.locator(".cc-content-value").all_text_contents()
                
                # Pulizia nomi
                partecipanti = [d.strip() for d in tutti_i_dati if len(d.strip()) > 3 and "€" not in d and "pdf" not in d.lower()]
                
                print(f"TORNEO: {nome_torneo.strip()}")
                print("PARTECIPANTI:")
                for p in partecipanti:
                    print(f"- {p.strip()}")
                print("-" * 30)
                    
            except Exception as e:
                # Se fallisce, fa uno screenshot e lo salva nei log/artifacts
                await page.screenshot(path=f"errore_{url.split('=')[-1]}.png")
                print(f"--- [ERRORE] su {url}: {e} (Screenshot salvato) ---")
                continue
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
