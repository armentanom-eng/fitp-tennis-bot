import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio del bot ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        print("--- Navigazione portale ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
	await page.locator('span:text-is("Roma")').last.click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # --- CICLO CARICA ALTRI ---
        print("--- Caricamento totale lista tornei ---")
        while True:
            btn_load_more = page.locator("button#btn-loadMore")
            if await btn_load_more.is_visible():
                print("    -> Trovato 'Carica altri', clicco...")
                await btn_load_more.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
            else:
                print("    -> Lista completa caricata.")
                break
        
        # Estrazione URL tornei dopo il caricamento completo
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei totali. ---")
        
        dati_giovanili = {"tornei": []}
        dati_open = {"tornei": []}
        
        for url in urls:
            await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
            
            # Chiudi cookie
            try:
                await page.get_by_role("button", name="Accetta").click(timeout=3000)
            except:
                pass
            
            # Trova bottoni Dettaglio
            dettagli = page.locator("text=Dettaglio >")
            count = await dettagli.count()
            
            for i in range(count):
                btn = page.locator("text=Dettaglio >").nth(i)
                try:
                    await btn.wait_for(state="visible", timeout=10000)
                    await btn.click(force=True)
                    await page.wait_for_load_state("networkidle")
                    
                    categoria = await page.locator("h1.cc-title-main").first.text_content()
                    giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                    
                    entry = {"torneo": url, "categoria": categoria.strip(), "iscritti": [g.strip() for g in giocatori]}
                    
                    if any(x in categoria for x in ["Under", "Giovanile", "U10", "U11", "U12", "U14", "U16"]):
                        dati_giovanili["tornei"].append(entry)
                    else:
                        dati_open["tornei"].append(entry)
                    
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
                except Exception as e:
                    print(f"    ! Errore su categoria {i}: {e}")
                    await page.goto(f"https://www.fitp.it{url}")
        
        # Salvataggio
        with open("Iscritti_Giovanili.json", "w", encoding="utf-8") as f: json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)


      
        await browser.close()
        print("--- [END] Processo completato. File generati. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
