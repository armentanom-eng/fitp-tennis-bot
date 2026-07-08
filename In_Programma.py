import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Diagnostica Bot ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()
        
        print("--- Navigazione portale ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        await page.click('button[data-id="select_status"]')
        await page.locator('span:text-is("In programma")').last.click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.locator('span:text-is("Roma")').last.click()      
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Estrazione URL
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. Analizzo SOLO il primo: {urls[0]} ---")
        
        # ANALISI SOLO DEL PRIMO TORNEO
        url = urls[0]
        await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
        
        # Log del titolo per capire se siamo sulla pagina giusta o su quella di errore
        print(f"Titolo pagina: {await page.title()}")
        
        # Vediamo se trova i bottoni
        dettagli = page.locator("text=Dettaglio >")
        count = await dettagli.count()
        print(f"Bottoni 'Dettaglio >' trovati: {count}")
        
        for i in range(count):
            print(f"--- Analisi Bottone {i} ---")
            try:
                btn = dettagli.nth(i)
                await btn.click(force=True)
                await page.wait_for_load_state("networkidle")
                
                # Debug: vediamo il titolo della categoria
                cat = await page.locator("h1.cc-title-main").first.text_content()
                print(f"Categoria trovata: {cat}")
                
                # Debug: vediamo se ci sono link giocatori
                giocatori = await page.locator("a[href*='Pagina-Giocatore']").all()
                print(f"Link giocatori trovati: {len(giocatori)}")
                
                # Se non ne trova, stampiamo il testo visibile per capire cosa c'è
                if len(giocatori) == 0:
                    testo_pagina = await page.inner_text("body")
                    print(f"Testo pagina estratto (primi 300 caratteri): {testo_pagina[:300]}")
                
                await page.go_back()
                await page.wait_for_load_state("networkidle")
                
            except Exception as e:
                print(f"Errore su bottone {i}: {e}")
        
        await browser.close()
        print("--- [END] Diagnostica completata ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
