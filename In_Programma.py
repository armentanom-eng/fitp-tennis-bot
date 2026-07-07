import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG] START: Avvio bot In_Programma completo ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        print("--- [LOG] Navigazione a Ricerca-tornei ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        
        # Filtri
        print("--- [LOG] Impostazione filtri: Lazio, Roma, In programma ---")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await asyncio.sleep(2)
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Caricamento lista
        print("--- [LOG] Caricamento elenco tornei ---")
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            print("--- [LOG] Cliccato 'Carica altri' ---")
            await asyncio.sleep(2)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        print(f"--- [LOG] Trovati {len(urls)} tornei totali ---")
        
        dati_iscritti_giov, dati_iscritti_open = {"tornei": []}, {"tornei": []}
        dati_partite_giov, dati_partite_open = {"tornei": []}, {"tornei": []}
        
        for idx, url in enumerate(urls):
            print(f"--- [LOG] ({idx+1}/{len(urls)}) Analisi: https://www.fitp.it{url} ---")
            await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
            
            # Selezione data
            select = page.locator("select#select-ordergame")
            if await select.is_visible():
                print("--- [LOG] Seleziono ultima data disponibile ---")
                await select.select_option(index=-1)
                await asyncio.sleep(2)
            
            # Categorie
            count = await page.locator("span:has-text('Dettaglio >')").count()
            print(f"--- [LOG] Trovate {count} categorie in questo torneo ---")
            
            for i in range(count):
                btn = page.locator("span:has-text('Dettaglio >')").nth(i)
                if await btn.is_visible():
                    print(f"--- [LOG] Clicco su 'Dettaglio' categoria {i+1} ---")
                    await btn.click(force=True)
                    await asyncio.sleep(3)
                    
                    cat_name = await page.locator("h1.cc-title-main").first.text_content()
                    print(f"--- [LOG] Categoria: {cat_name.strip()} ---")
                    
                    # Estrazione Iscritti
                    nomi = await page.locator(".cc-content-value .cc-title").all_text_contents()
                    print(f"--- [LOG] Estratti {len(nomi)} iscritti ---")
                    
                    # Estrazione PDF sicura
                    pdf_locator = page.locator("a#btnOrderGameDownload")
                    if await pdf_locator.count() > 0:
                        link_pdf = await pdf_locator.get_attribute("href")
                    else:
                        link_pdf = None
                    
                    entry_isc = {"torneo": url, "categoria": cat_name.strip(), "iscritti": [n.strip() for n in nomi if n.strip()]}
                    entry_part = {"torneo": url, "categoria": cat_name.strip(), "partita_pdf": link_pdf}
                    
                    if any(x in cat_name for x in ["Under", "Giovanile", "U10", "U11", "U12", "U14", "U16"]):
                        dati_iscritti_giov["tornei"].append(entry_isc)
                        dati_partite_giov["tornei"].append(entry_part)
                    else:
                        dati_iscritti_open["tornei"].append(entry_isc)
                        dati_partite_open["tornei"].append(entry_part)
                    
                    await page.go_back()
                    await page.wait_for_selector("span:has-text('Dettaglio >')")
                else:
                    print(f"--- [LOG] Bottone categoria {i+1} non trovato, salto ---")
        
        # Salvataggio
        print("--- [LOG] Salvataggio JSON completato ---")
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_iscritti_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_iscritti_open, f, ensure_ascii=False, indent=4)
        with open("Partite_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_partite_giov, f, ensure_ascii=False, indent=4)
        with open("Partite_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_partite_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [LOG] END: Processo concluso con successo ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
