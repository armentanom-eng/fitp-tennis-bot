import asyncio
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

CATEGORIES = {
    "t_giovanili": "Giovanili_Partite.json", 
    "t_affiliati": "Open_Partite.json"
}

STATUSES = ["In corso", "Iscrizioni aperte"]

def format_line_for_swift(raw_text, date_target):
    text = raw_text.replace("\n", " ").strip()
    match_time = re.search(r"(\d{2})[:.](\d{2})", text)
    time = f"{match_time.group(1)}:{match_time.group(2)}" if match_time else "00:00"
    
    text = re.sub(r"(INIZIO|ORE|NON PRIMA DI|TABELLONE)?[:\s]*\d{2}[:.]\d{2}", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+o\s+", " vs ", text, flags=re.IGNORECASE)
    
    partite = re.findall(r"([A-Z\s\d\(\)]+?)\s+vs\s+([A-Z\s\d\(\)]+)", text)
    if partite:
        clean = [f"{p[0].strip()} vs {p[1].strip()}" for p in partite]
        return f"{date_target}; {time}; {'; '.join(clean)}"
    return f"{date_target}; {time}; {text.strip()}"

def get_pdf_info(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        row_text = " ".join([str(cell).strip() for cell in row if cell])
                        if len(row_text) > 5: matches.append(row_text)
    except: pass
    return matches

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"--- Inizio scansione categoria: {cat_id} ---")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            for status in STATUSES:
                print(f"Analizzando stato: {status}...")
                await page.goto(BASE_URL, wait_until="networkidle")
                
                await page.click('button[data-id="select_status"]')
                await page.get_by_role("listbox").get_by_role("option", name=status).click()
                
                await page.click('button[data-id="id_regioneSearch"]')
                await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
                
                print(f"Clicco sul filtro: {cat_id}")
                await page.locator(f'a[data-id="{cat_id}"]').first.click()
                await asyncio.sleep(4)
                
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                
                print(f"Trovati {len(links)} tornei per {status}")
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        
                        # ESTRAZIONE NOME TORNEO DALLA PAGINA
                        nome_torneo = await page.title()
                        nome_torneo = nome_torneo.replace(" - FITP", "").strip()
                        
                        if not await page.locator("#select-ordergame").is_visible(): continue
                        
                        for i in range(2):
                            data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                            if await page.locator(f"#select-ordergame option:has-text('{data_target}')").count() > 0:
                                await page.select_option("#select-ordergame", label=data_target)
                                await asyncio.sleep(2)
                                download_btn = page.locator("#btnOrderGameDownload")
                                if await download_btn.is_visible():
                                    async with page.expect_download() as dl_info: await download_btn.click()
                                    download = await dl_info.value
                                    await download.save_as("temp.pdf")
                                    matches = get_pdf_info("temp.pdf")
                                    if matches:
                                        json_data["tornei"].append({
                                            "url": full_url, 
                                            "nomeTorneo": nome_torneo,
                                            "data": data_target, 
                                            "partite": [format_line_for_swift(m, data_target) for m in matches]
                                        })
                    except Exception as e:
                        print(f"Errore su {full_url}: {e}")
                        
            with open(filename, "w", encoding="utf-8") as f: 
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            print(f"Salvato file: {filename}")
            await page.close()
            
        await browser.close()
        print("Scansione completa!")

if __name__ == "__main__": asyncio.run(run_bot())
