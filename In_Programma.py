import asyncio
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio Scraper Tornei FITP ---")
    
    async with async_playwright() as p:
        # Avvio browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # 1. Navigazione e Filtri
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        print("--- [DEBUG] Impostazione filtri ---")
        
        # Filtri (Selettori basati sulle tue ispezioni)
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
        print(f"--- [INFO] Trovati {len(urls)} tornei ---")
        
        # 2. Iterazione su ogni torneo
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            try:
                await page.goto(full_url, wait_until="domcontentloaded")
                
                # Trova tutti i "Dettaglio >"
                dettagli = page.locator("span.cc-subtitle:has-text('Dettaglio >')")
                count = await dettagli.count()
                
                if count == 0:
                    continue # Salta se non trova nulla

                for i in range(count):
                    # Ricalcola il bottone per evitare errori di DOM
                    bottone = page.locator("span.cc-subtitle:has-text('Dettaglio >')").nth(i)
                    await bottone.evaluate("el => el.click()")
                    await asyncio.sleep(2)
                    
                    # Estrazione dati
                    nome_torneo = await page.locator("h1.cc-title-main").first.text_content()
                    categoria = await page.locator(".cc-title-main").nth(1).text_content()
                    
                    # Lista Partecipanti filtrata
                    tutti_i_dati = await page.locator(".cc-content-value").all_text_contents()
                    partecipanti = [
                        d.strip() for d in tutti_i_dati 
                        if len(d.strip()) > 3 
                        and "€" not in d 
                        and "pdf" not in d.lower()
                        and "non ancora" not in d.lower()
                    ]
                    
                    # STAMPA FORMATTATA
                    print(f"TORNEO: {nome_torneo.strip()}")
                    print(f"CATEGORIA: {categoria.strip()}")
                    print("PARTECIPANTI:")
                    for p in partecipanti:
                        print(f"- {p.strip()}")
                    print("-" * 30)
                    
                    await page.go_back()
                    await page.wait_for_load_state("domcontentloaded")
                    
            except Exception as e:
                print(f"--- [ERRORE] su {url}: {e} ---")
                continue
                
        await browser.close()
        print("--- [END] Processo completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
