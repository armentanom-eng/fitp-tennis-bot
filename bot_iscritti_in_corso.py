import asyncio
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

CATEGORIES = {
    "t_giovanili": "Giovanili_Partite_incorsopdf.json", 
    "t_affiliati": "Open_Partite_incorsopdf.json"
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
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            
            # FILTRI: Selezione specifica per evitare link esterni
            for filter_name, value in [('select_status', 'In corso'), ('id_regioneSearch', 'Lazio'), ('id_provinciaSearch', 'Roma')]:
                await page.click(f'button[data-id="{filter_name}"]')
                # Cerchiamo l'opzione solo dentro il menu a tendina aperto (.show)
                opt = page.locator(f"div.dropdown-menu.show a:has-text('{value}')").first
                await opt.wait_for(state="visible", timeout=10000)
                await opt.click()
                await page.wait_for_load_state("networkidle")
            
            # Selezione Categoria
            await page.wait_for_selector(f'a[data-id="{cat_id}"]')
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await page.wait_for_load_state("networkidle")
            
            # ESPANSIONE
            while True:
                more_btn = page.locator("#btn-loadMore")
                if await more_btn.is_visible():
                    await more_btn.click()
                    await page.wait_for_load_state("networkidle")
                else:
                    break
            
            links = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
            print(f"   [Tornei trovati]: {len(links)}")
            
            for link in links:
                try:
                    await page.goto(f"https://www.fitp.it{link}", wait_until="networkidle", timeout=60000)
                    nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                    
                    dropdown = page.locator("#select-ordergame")
                    download_btn = page.locator("#btnOrderGameDownload")
                    
                    partite_totali = []
                    if await dropdown.is_visible():
                        for i in range(0, 2): 
                            data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                            if await page.locator(f"#select-ordergame option:has-text('{data_target}')").count() > 0:
                                await page.select_option("#select-ordergame", label=data_target)
                                await page.wait_for_load_state("networkidle")
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
                    print(f"   [Errore su torneo]: {e}")
                    continue 
            
            with open(filename, "w", encoding="utf-8") as f: 
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            await page.close()
        
        await browser.close()
    print("--- [END] Processo completato correttamente ---")

if __name__ == "__main__": 
    asyncio.run(run_bot())
