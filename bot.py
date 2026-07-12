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

def get_pdf_info_filtered(pdf_path):
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        row_data = [str(cell).strip() for cell in row if cell and str(cell).strip() not in ["-", ""]]
                        if row_data:
                            row_text = " ".join(row_data)
                            if (oggi in row_text or domani in row_text) or len(row_data) >= 2:
                                matches.append(row_text)
    except Exception as e:
        print(f"Errore parsing PDF: {e}")
    return matches

def format_line_for_swift(raw_text, date_target):
    text = re.sub(r"(INIZIO|ORE|NON PRIMA DI|TABELLONE)?[:\s]*\d{2}[:.]\d{2}", "", raw_text, flags=re.IGNORECASE)
    text = re.sub(r"\s+o\s+", " vs ", text, flags=re.IGNORECASE)
    partite = re.findall(r"([A-Z\s\d\(\)\.\-]+?)\s+(?:vs|o|contro)\s+([A-Z\s\d\(\)\.\-]+)", text, re.IGNORECASE)
    if partite:
        return f"{date_target}; 00:00; {'; '.join([f'{p[0].strip()} vs {p[1].strip()}' for p in partite])}"
    return f"{date_target}; 00:00; {text.strip()}"

async def run_bot():
    print("--- [START] Avvio estrazione corretta ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            await page.goto(BASE_URL, timeout=60000)
            
            # Filtri
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
            await asyncio.sleep(2)
            
            await page.wait_for_selector(f'a[data-id="{cat_id}"]')
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(5)
            
            while await page.locator("#btn-loadMore").is_visible():
                await page.locator("#btn-loadMore").click()
                await asyncio.sleep(3)
            
            await page.wait_for_load_state("networkidle")
            links = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
            
            for link in links:
                await page.goto(f"https://www.fitp.it{link}", timeout=60000)
                await page.wait_for_load_state("networkidle")
                
                download_btn = page.locator("a:has-text('Scarica'), button:has-text('Scarica'), #btnOrderGameDownload")
                
                partite_trovate = []
                if await download_btn.first.is_visible():
                    try:
                        async with page.expect_download(timeout=45000) as dl_info:
                            await download_btn.first.click()
                        
                        download = await dl_info.value
                        pdf_path = await download.path() # Corretto: Await aggiunto
                        
                        matches = get_pdf_info_filtered(pdf_path)
                        partite_trovate = [format_line_for_swift(m, "Oggi") for m in matches]
                    except Exception as e:
                        print(f"   [Skip]: {link} - Errore download: {e}")
                
                if partite_trovate:
                    json_data["tornei"].append({
                        "url": f"https://www.fitp.it{link}",
                        "nomeTorneo": await page.locator("h1").first.inner_text(),
                        "data": datetime.now().strftime("%d/%m/%Y"),
                        "partite": partite_trovate
                    })

            with open(filename, "w", encoding="utf-8") as f: json.dump(json_data, f, ensure_ascii=False, indent=4)
            await page.close()
        await browser.close()
    print("--- [END] Processo completato ---")

if __name__ == "__main__": asyncio.run(run_bot())
