import asyncio
import os
import pdfplumber
import re
import json
from playwright.async_api import async_playwright

def get_pdf_info(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        for cell in row:
                            if cell and ("Inizio ore" in cell or "Non prima delle" in cell):
                                matches.append(cell.replace("\n", " ").strip())
    except: pass
    return matches

async def run_bot():
    print("--- [START] Avvio Bot Debug Unificato ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        
        # Filtri
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await asyncio.sleep(2)
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await asyncio.sleep(2)
            
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        results = {"giovanili": {"iscritti": [], "partite": []}, "open": {"iscritti": [], "partite": []}}
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            await page.goto(full_url, wait_until="domcontentloaded")
            
            # Recuperiamo i link di dettaglio
            links = await page.locator("a[href*='Dettaglio-Competizione']").all()
            
            for link in links:
                try:
                    await link.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(2) # Pausa necessaria per il rendering
                    
                    cat = await page.locator("h1.cc-title-main").first.text_content()
                    cat = cat.strip() if cat else "Senza Categoria"
                    
                    # LOG DI DEBUG: Controlliamo cosa vede il bot
                    gioc_locator = page.locator("a[href*='Pagina-Giocatore']")
                    count_gioc = await gioc_locator.count()
                    print(f"DEBUG: Categoria {cat} | Iscritti trovati: {count_gioc}")
                    
                    gioc = [await el.text_content() for el in await gioc_locator.all()]
                    
                    is_g = any(x in cat for x in ["Under", "Giovanile", "U10", "U11", "U12", "U14", "U16"])
                    key = "giovanili" if is_g else "open"
                    
                    results[key]["iscritti"].append({"cat": cat, "iscritti": [g.strip() for g in gioc]})
                    
                    # PDF
                    if await page.locator("#btnOrderGameDownload").is_visible(timeout=3000):
                        async with page.expect_download() as dl_info:
                            await page.click("#btnOrderGameDownload")
                        path = "temp.pdf"
                        await (await dl_info.value).save_as(path)
                        matches = get_pdf_info(path)
                        results[key]["partite"].append({"cat": cat, "partite": matches})
                        if os.path.exists(path): os.remove(path)
                    
                    await page.go_back()
                    await page.wait_for_load_state("domcontentloaded")
                    
                except Exception as e:
                    print(f"    ! Errore categoria: {e}")
                    await page.goto(full_url)
        
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f: json.dump(results["giovanili"]["iscritti"], f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(results["open"]["iscritti"], f, ensure_ascii=False, indent=4)
        with open("Partite_Giovanili_In_Programma.json", "w", encoding="utf-8") as f: json.dump(results["giovanili"]["partite"], f, ensure_ascii=False, indent=4)
        with open("Partite_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(results["open"]["partite"], f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
