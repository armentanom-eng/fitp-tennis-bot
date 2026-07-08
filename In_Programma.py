import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio Bot Ottimizzato ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()
        
        # Timeout globale per evitare blocchi infiniti
        page.set_default_timeout(60000) 

        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        # [.. le tue selezioni filtri restano invariate ..]
        await asyncio.sleep(3)
        
        # Caricamento lista
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await asyncio.sleep(1)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        dati_giov, dati_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            print(f"Analisi: {full_url}")
            await page.goto(full_url, wait_until="domcontentloaded")
            
            # Recuperiamo tutti i bottoni una volta sola per pagina
            dettagli = page.locator("span:has-text('Dettaglio >')")
            count = await dettagli.count()
            
            for i in range(count):
                # Usiamo locator dinamico per non perdere il riferimento
                btn = page.locator("span:has-text('Dettaglio >')").nth(i)
                await btn.click()
                
                # Attesa specifica per il contenuto che ti serve invece di 'networkidle'
                await page.locator("h1.cc-title-main").wait_for()
                
                categoria = await page.locator("h1.cc-title-main").first.text_content()
                giocatori = await page.locator(".cc-content-value").all_text_contents()
                lista_nomi = [g.strip() for g in giocatori if g.strip()]
                
                entry = {"torneo": url, "categoria": categoria.strip(), "iscritti": lista_nomi}
                
                if any(x in categoria for x in ["Under", "Giovanile", "U10", "U12", "U14", "U16"]):
                    dati_giov["tornei"].append(entry)
                else:
                    dati_open["tornei"].append(entry)
                
                # Torniamo indietro nella pagina del torneo invece di ricaricare tutto
                await page.go_back(wait_until="domcontentloaded")
        
        # Salvataggio.. (come da tuo codice)
        await browser.close()
        print("--- [END] Processo completato ---")
