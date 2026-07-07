import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio del bot ---")
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
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        dati_giovanili = {"tornei": []}
        dati_open = {"tornei": []}
        
        for url in urls:
            await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
            
            # --- AZIONE CRITICA: CHIUDIAMO I COOKIE ---
            # Cerchiamo il bottone "Accetta" dell'informativa cookie
            try:
                await page.get_by_role("button", name="Accetta").click(timeout=3000)
                print("    -> Cookie accettati.")
            except:
                pass # Se non c'è, proseguiamo
            
            # --- CERCHIAMO I BOTTONI IN MODO ESPLICITO ---
            # Cerchiamo tutti gli elementi che contengono la parola "Dettaglio"
            dettagli = page.locator("xpath=//span[contains(text(), 'Dettaglio')]")
            count = await dettagli.count()
            print(f"    -> Trovati {count} blocchi categoria.")
            
            for i in range(count):
                # Clicchiamo lo span che dice Dettaglio
                await dettagli.nth(i).click()
                await page.wait_for_load_state("networkidle")
                
                categoria = await page.locator("h1.cc-title-main").first.text_content()
                print(f"       -> Analisi: {categoria.strip()}")
                
                # Estraiamo i nomi
                giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                
                entry = {"torneo": url, "categoria": categoria.strip(), "iscritti": [g.strip() for g in giocatori]}
                
                if "Under" in categoria or "Giovanile" in categoria:
                    dati_giovanili["tornei"].append(entry)
                else:
                    dati_open["tornei"].append(entry)
                
                # Torniamo indietro
                await page.go_back()
                await page.wait_for_load_state("networkidle")
        
        with open("Iscritti_Giovanili.json", "w", encoding="utf-8") as f:
            json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_Giovanili.json", "w", encoding="utf-8") as f:
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
