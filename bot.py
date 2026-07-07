import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio del bot ---")
    
    async with async_playwright() as p:
        # Configurazione standard per GitHub Actions
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        
        print("--- Navigazione portale ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        print("--- Impostazione Filtri ---")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5) 
        
        # Estrazione Tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. ---")
        
        risultati = []
        
        for idx, url in enumerate(urls, 1):
            full_url = f"https://www.fitp.it{url}"
            print(f"[{idx}/{len(urls)}] Analisi Torneo: {full_url}")
            
            await page.goto(full_url, wait_until="networkidle")
            await asyncio.sleep(3) # Pausa di sicurezza per il rendering JS
            
            # Contiamo i tasti "Dettaglio"
            tasti_dettaglio = page.locator("a:has-text('Dettagli')")
            count = await tasti_dettaglio.count()
            print(f"    -> Trovati {count} bottoni 'Dettagli'.")
            
            if count == 0:
                print("    ! DEBUG: Nessun bottone trovato. Stampo anteprima pagina...")
                print(await page.inner_text("body", timeout=5000))
                continue
            
            for i in range(count):
                # Ricarichiamo il riferimento al tasto i-esimo
                btn = page.locator("a:has-text('Dettagli')").nth(i)
                await btn.click()
                await page.wait_for_load_state("networkidle")
                
                # Lista giocatori
                giocatori = await page.locator("a[href*='Pagina-Giocatore']").all()
                print(f"       -> Categoria {i+1}: estratti {len(giocatori)} giocatori.")
                
                for g_link in giocatori:
                    g_url = await g_link.get_attribute("href")
                    await page.goto(f"https://www.fitp.it{g_url}", wait_until="domcontentloaded")
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    
                    risultati.append({"torneo": full_url, "nome": nome.strip()})
                    print(f"          + {nome.strip()}")
                    
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
                
                # Torniamo al dettaglio torneo principale
                await page.goto(full_url, wait_until="networkidle")
        
        with open("Risultati_Finali.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        print("--- [FINE] Estrazione completata. ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
