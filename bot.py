import asyncio
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

CATEGORIES = {
    "t_giovanili": "Iscrizioni_Aperte_Giovanili_pdf.json", 
    "t_affiliati": "Iscrizioni_Aperte_Open_pdf.json"
}

def get_pdf_info(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        row_text = " ".join([str(cell).strip() for cell in row if cell and str(cell).strip()])
                        if len(row_text) > 5: matches.append(row_text)
    except: pass
    return matches

def format_line_for_swift(raw_text, date_target):
    clean_text = raw_text.replace('\n', ' ').strip()
    return f"{date_target}; {clean_text}"

async def run_bot():
    print("--- [START] Avvio estrazione completa e resistente ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            await page.goto(BASE_URL, timeout=60000)
            
            # --- FILTRI RIGIDI ---
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
            await asyncio.sleep(3)
            
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(4) 
            
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(4)
            
            await page.wait_for_selector(f'a[data-id="{cat_id}"]')
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(6) 
            
            # --- ESPANSIONE AGGRESSIVA ---
            while True:
                more_btn = page.locator("#btn-loadMore")
                if await more_btn.is_visible():
                    await more_btn.click()
                    await asyncio.sleep(6)
                else:
                    break
            
            links = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
            print(f"   [Tornei trovati]: {len(links)}")
            
            for link in links:
                try:
                    await page.goto(f"https://www.fitp.it{link}", timeout=60000)
                    await page.wait_for_load_state("networkidle")
                    
                    try:
                        nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                    except:
                        nome_torneo = "Torneo senza nome"
                    
                    print(f"   [Analizzo]: {nome_torneo.strip()}")
                    
                    dropdown_selector = "#select-ordergame"
                    download_btn = page.locator("#btnOrderGameDownload")
                    
                    partite_totali = []
                    if await page.locator(dropdown_selector).is_visible():
                        for i in range(0, 2): 
                            data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                            
                            if await page.locator(f"{dropdown_selector} option:has-text('{data_target}')").count() > 0:
                                await page.select_option(dropdown_selector, label=data_target)
                                await asyncio.sleep(5)
                                
                                if await download_btn.is_visible():
                                    async with page.expect_download(timeout=30000) as dl_info: 
                                        await download_btn.click()
                                    download = await dl_info.value
                                    path = await download.path()
                                    matches = get_pdf_info(path)
                                    for m in matches:
                                        partite_totali.append(format_line_for_swift(m, data_target))
                    
                    if partite_totali:
                        json_data["tornei"].append({
                            "url": f"https://www.fitp.it{link}", 
                            "nomeTorneo": nome_torneo.strip(), 
                            "data": datetime.now().strftime("%d/%m/%Y"), 
                            "partite": list(set(partite_totali))
                        })
                except Exception as e:
                    print(f"   [Errore su torneo]: {e}. Salto al prossimo.")
                    continue 
            
            with open(filename, "w", encoding="utf-8") as f: 
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            await page.close()
        
        await browser.close()
    print("--- [END] Processo completato correttamente ---")

if __name__ == "__main__": 
    asyncio.run(run_bot())
