import asyncio
from playwright.async_api import async_playwright

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Navigazione e Filtri (usando le tue ispezioni)
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        # ... (applica filtri come concordato) ...
        await page.locator('#btn-search').click()
        await asyncio.sleep(5)
        
        # Recupera URL tornei
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        # 2. Iterazione su ogni torneo
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            await page.goto(full_url, wait_until="domcontentloaded")
            
            # Trova tutti i "Dettaglio >"
            dettagli = page.locator("span.cc-subtitle:has-text('Dettaglio >')")
            count = await dettagli.count()
            
            # Se ci sono sottocategorie (es. Singolare Maschile/Femminile)
            for i in range(count):
                # Clicca per espandere
                await dettagli.nth(i).evaluate("el => el.click()")
                await asyncio.sleep(1)
                
                # Nome Torneo (h1 principale)
                nome_torneo = await page.locator("h1.cc-title-main").first.text_content()
                # Categoria (quella che abbiamo appena cliccato)
                categoria = await page.locator(".cc-title-main").nth(1).text_content()
                
                # Lista Partecipanti
                # Basato sulla tua ispezione: .cc-section-players
                partecipanti = await page.locator(".cc-content-value").all_text_contents()
                
                # STAMPA A VIDEO FORMATTATA
                print(f"TORNEO: {nome_torneo.strip()}")
                print(f"CATEGORIA: {categoria.strip()}")
                print("PARTECIPANTI:")
                for p in partecipanti:
                    if p.strip():
                        print(f"- {p.strip()}")
                print("-" * 30) # Separatore
                
                # Torna indietro per la prossima categoria
                await page.go_back()
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
