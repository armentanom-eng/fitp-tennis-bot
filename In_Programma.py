import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG] Avvio bot unificato ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        # Navigazione iniziale
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri (Selettori presi dal tuo secondo esempio che funzionano meglio)
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Caricamento lista completa
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await asyncio.sleep(2)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        dati_iscritti, dati_pdf = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            try:
                full_url = f"https://www.fitp.it{url}"
                await page.goto(full_url, wait_until="networkidle")
                
                cat_name = await page.locator("h1.cc-title-main").first.text_content()
                
                # --- ESTRAZIONE ISCRITTI (Metodo robusto secondo esempio) ---
                giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                
                # --- ESTRAZIONE PDF (Controllo preventivo) ---
                pdf_locator = page.locator("a#btnOrderGameDownload")
                link_pdf = await pdf_locator.get_attribute("href") if await pdf_locator.count() > 0 else None
                
                # Salvataggio
                dati_iscritti["tornei"].append({"torneo": url, "categoria": cat_name.strip(), "iscritti": [g.strip() for g in giocatori]})
                dati_pdf["tornei"].append({"torneo": url, "categoria": cat_name.strip(), "pdf": link_pdf})
                
                print(f"--- [LOG] Analizzato: {cat_name.strip()[:20]} | Iscritti: {len(giocatori)} | PDF: {'Trovato' if link_pdf else 'No'} ---")
            
            except Exception as e:
                print(f"--- [LOG] Errore su {url}: {e} ---")
                continue

        # Salvataggio su file
        with open("Iscritti_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_iscritti, f, ensure_ascii=False, indent=4)
        with open("Partite_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_pdf, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [LOG] Processo terminato con successo ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
