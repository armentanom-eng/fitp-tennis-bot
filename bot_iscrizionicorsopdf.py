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

def get_target_dates():
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    return [oggi, domani]

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

def get_pdf_info_filtered(pdf_path, target_dates):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        row_text = " ".join([str(cell).strip() for cell in row if cell])
                        # Filtro: teniamo solo le righe che contengono la data di oggi o domani
                        if any(d in row_text for d in target_dates):
                            matches.append(row_text)
    except: pass
    return matches

async def run_bot():
    print("--- [START] Avvio estrazione PROGRAMMI GARE (In corso + Filtro Date) ---")
    target_dates = get_target_dates()
    print(f"-> Filtro attivo per date: {target_dates}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Processo categoria: {cat_id}")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Filtri
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name="In corso").click()
            await asyncio.sleep(2)
            
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(2)
            
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(2)
            
            # Selezione Categoria specifica
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(5)
            
            # Loop "Carica altri"
            print("-> Espansione lista tornei...")
            while True:
                btn = page.locator("#btn-loadMore")
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(4)
                else:
                    break
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                await page.goto(full_url, wait_until="domcontentloaded")
                
                nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                print(f"   [Analizzo]: {nome_torneo.strip()}")
                
                download_btn = page.locator("#btnOrderGameDownload")
                if await download_btn.is_visible():
                    async with page.expect_download() as dl_info: 
                        await download_btn.click()
                    download = await dl_info.value
                    await download.save_as("temp.pdf")
                    
                    # Estrazione filtrata per data
                    matches = get_pdf_info_filtered("temp.pdf", target_dates)
                    
                    if matches:
                        json_data["tornei"].append({
                            "url": full_url, 
                            "nomeTorneo": nome_torneo.strip(), 
                            "partite": [format_line_for_swift(m, datetime.now().strftime("%d/%m/%Y")) for m in matches]
                        })
            
            with open(filename, "w", encoding="utf-8") as f: 
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            await page.close()
        await browser.close()
    print("--- [END] Processo completato ---")

if __name__ == "__main__": 
    asyncio.run(run_bot())
