import asyncio
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

async def run_bot():
    print("--- Avvio estrazione tornei oggi e domani ---")
    oggi = datetime.now().date()
    domani = oggi + timedelta(days=1)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        await page.click('button[data-id="select_status"]')
        await page.locator('span:text-is("In programma")').last.click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Espansione lista
        while True:
            btn = page.locator("button#btn-loadMore")
            if await btn.is_visible(): await btn.click(); await page.wait_for_load_state("networkidle"); await asyncio.sleep(2)
            else: break
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        dati_giovanili, dati_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
            
            # FILTRO DATA
            try:
                # Modifica il selettore '.data-torneo' con quello corretto del sito
                data_el = page.locator(".data-torneo").first
                data_text = await data_el.text_content()
                data_torneo = datetime.strptime(data_text.strip(), "%d/%m/%Y").date()
                
                if data_torneo not in [oggi, domani]:
                    print(f"    -> Saltato torneo {url[-5:]}: data {data_text}")
                    continue
            except:
                continue # Salta se non trova la data
            
            # Estrazione Dettagli (come fatto in precedenza)
            count = await page.locator("text=Dettaglio >").count()
            for i in range(count):
                await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
                btn = page.locator("text=Dettaglio >").nth(i)
                await btn.click(force=True)
                
                categoria = await page.locator("h1.cc-title-main").first.text_content()
                tabellone = await page.locator("span#spn-tournament-description").text_content()
                giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                
                entry = {"torneo": url, "categoria": categoria.strip(), "tabellone": tabellone.strip(), "iscritti": [g.strip() for g in giocatori]}
                
                if any(x in categoria.lower() for x in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                    dati_giovanili["tornei"].append(entry)
                else:
                    dati_open["tornei"].append(entry)
        
        with open("Tornei_Date_Giovanili_In_Programma_PDF.json", "w", encoding="utf-8") as f: json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Tornei_Date_Open_In_Programa_Pdf.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
