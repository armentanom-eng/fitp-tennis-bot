import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio estrazione ISCRITTI (Tornei in Corso) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(60000) # Aumentato a 60s per sicurezza
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        
        # FILTRO: In Corso (Approccio forzato)
        await page.click('button[data-id="select_status"]')
        # Cerchiamo l'elemento <a> che contiene esattamente "In corso" dentro il menu
        await page.locator('div.dropdown-menu.open a:has-text("In corso")').click(force=True)
        
        await asyncio.sleep(3) # Tempo necessario al caricamento dati dinamici
        
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.locator('span:text-is("Roma")').last.click()      
        await page.keyboard.press("Enter")
        await asyncio.sleep(8) 
        
        # --- (Il resto del tuo codice rimane invariato) ---
        while True:
            btn_load_more = page.locator("button#btn-loadMore")
            if await btn_load_more.is_visible():
                await btn_load_more.click()
                await asyncio.sleep(3)
            else: break
        
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            try:
                await page.goto(full_url, wait_until="domcontentloaded")
                nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                
                count = await page.locator("text=Dettaglio >").count()
                for i in range(count):
                    await page.goto(full_url, wait_until="domcontentloaded")
                    btn = page.locator("text=Dettaglio >").nth(i)
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await page.wait_for_load_state("domcontentloaded")
                        
                        categoria = await page.locator("h1.cc-title-main").first.text_content()
                        tabellone = await page.locator("span#spn-tournament-description").text_content() or "N/A"
                        giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                        
                        entry = {
                            "nomeTorneo": nome_torneo.strip(),
                            "categoria": categoria.strip(), 
                            "tabellone": tabellone.strip(), 
                            "iscritti": [g.strip() for g in giocatori]
                        }
                        
                        if any(x in categoria.lower() for x in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                            dati_giovanili["tornei"].append(entry)
                        else:
                            dati_open["tornei"].append(entry)
            except Exception as e: print(f"Errore su {url}: {e}")
        
        with open("Iscritti_Giovanili_In_Corso.json", "w", encoding="utf-8") as f: json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Corso.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
        await browser.close()

if __name__ == "__main__": asyncio.run(run_bot())
