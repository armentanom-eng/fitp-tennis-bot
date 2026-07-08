import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [LOG] START: Avvio bot In_Programma correzione selettori ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri (confermato dai tuoi screen)
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Caricamento
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await asyncio.sleep(2)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        dati_iscritti_open, dati_partite_open = {"tornei": []}, {"tornei": []}
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            await page.goto(full_url, wait_until="networkidle")
            
            # --- CORREZIONE SELETTORI ---
            # 1. Recupero Nomi (usiamo il container dei partecipanti che hai fotografato)
            # Dallo screen 18.57.53, i nomi sono dentro elementi .cc-field o simili
            nomi = await page.locator(".cc-content-value .cc-title, .cc-field span.cc-title").all_text_contents()
            
            # 2. Recupero PDF (dallo screen 18.55.01 il bottone ha id="btnOrderGameDownload")
            # Ma ora usiamo un selettore che intercetta meglio l'href
            pdf_link = await page.locator("a#btnOrderGameDownload").get_attribute("href")
            
            # Recupero Titolo Categoria
            cat_name = await page.locator("h1.cc-title-main").first.text_content()
            
            entry_isc = {"torneo": url, "categoria": cat_name.strip(), "iscritti": [n.strip() for n in nomi if n.strip()]}
            entry_part = {"torneo": url, "categoria": cat_name.strip(), "partita_pdf": pdf_link}
            
            dati_iscritti_open["tornei"].append(entry_isc)
            dati_partite_open["tornei"].append(entry_part)
            print(f"--- [LOG] Estratti {len(nomi)} nomi per {cat_name.strip()} ---")

        # Salvataggio
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_iscritti_open, f, ensure_ascii=False, indent=4)
        with open("Partite_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_partite_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [LOG] FINE: Salvataggio completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
