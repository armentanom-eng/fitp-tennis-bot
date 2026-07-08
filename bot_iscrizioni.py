import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio estrazione completa ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Carica tutta la lista
        while True:
            btn_load_more = page.locator("button#btn-loadMore")
            if await btn_load_more.is_visible():
                await btn_load_more.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
            else:
                break
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
            
            count = await page.locator("text=Dettaglio >").count()
            for i in range(count):
                # Ricarica per evitare blocchi
                await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
                btn = page.locator("text=Dettaglio >").nth(i)
                
                try:
                    await btn.click(force=True)
                    await page.wait_for_load_state("networkidle")
                    
                    categoria = await page.locator("h1.cc-title-main").first.text_content()
                    # Estrazione Tabellone corretta
                    tabellone_el = page.locator("span#spn-tournament-description")
                    tabellone = await tabellone_el.text_content() if await tabellone_el.count() > 0 else "N/A"
                    
                    giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                    
                    entry = {
                        "torneo": url, 
                        "categoria": categoria.strip(), 
                        "tabellone": tabellone.strip(), 
                        "iscritti": [g.strip() for g in giocatori]
                    }
                    
                    if any(x in categoria.lower() for x in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                        dati_giovanili["tornei"].append(entry)
                    else:
                        dati_open["tornei"].append(entry)
                except Exception as e:
                    print(f"    ! Errore su dettaglio {i}: {e}")
        
        with open("Iscritti_Giovanili.json", "w", encoding="utf-8") as f: json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
