import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG] START: Avvio bot In_Programma definitivo ---")
    async with async_playwright() as p:
        # Avvio browser
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        print("--- [LOG] Navigazione sito ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        print("--- [LOG] Impostazione filtri ---")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Espansione lista
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await asyncio.sleep(2)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        print(f"--- [LOG] Trovati {len(urls)} tornei. Inizio estrazione ---")
        
        dati_iscritti_open, dati_partite_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            try:
                await page.goto(full_url, wait_until="networkidle")
                
                # Nome categoria
                cat_name_el = page.locator("h1.cc-title-main").first
                cat_name = await cat_name_el.text_content() if await cat_name_el.count() > 0 else "Sconosciuta"
                
                # Nomi iscritti
                nomi = await page.locator(".cc-content-value .cc-title, .cc-field span.cc-title").all_text_contents()
                
                # PDF (Controllo di sicurezza)
                pdf_locator = page.locator("a#btnOrderGameDownload")
                if await pdf_locator.count() > 0:
                    link_pdf = await pdf_locator.get_attribute("href")
                else:
                    link_pdf = None
                
                # Salvataggio in memoria
                entry_isc = {"torneo": url, "categoria": cat_name.strip(), "iscritti": [n.strip() for n in nomi if n.strip()]}
                entry_part = {"torneo": url, "categoria": cat_name.strip(), "partita_pdf": link_pdf}
                
                dati_iscritti_open["tornei"].append(entry_isc)
                dati_partite_open["tornei"].append(entry_part)
                print(f"--- [LOG] OK: {cat_name.strip()[:20]}... | Iscritti: {len(nomi)} ---")
                
            except Exception as e:
                print(f"--- [LOG] ERRORE sul torneo {url}: {e} ---")
                continue

        # Salvataggio finale
        print("--- [LOG] Salvataggio JSON ---")
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_iscritti_open, f, ensure_ascii=False, indent=4)
        with open("Partite_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_partite_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [LOG] Salvataggio completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
