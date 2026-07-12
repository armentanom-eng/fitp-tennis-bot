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

# Funzione per filtrare solo i dati di oggi e domani
def get_pdf_info_filtered(pdf_path):
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        row_text = " ".join([str(cell).strip() for cell in row if cell])
                        if len(row_text) > 5 and (oggi in row_text or domani in row_text):
                            matches.append(row_text)
    except: pass
    return matches

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

async def run_bot():
    print("--- [START] Avvio estrazione (Corretto con await .all()) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            await page.goto(BASE_URL, timeout=60000)
            
            # Filtri base
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
            await asyncio.sleep(2)
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(2)
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(2)
            
            cat_selector = f'a[data-id="{cat_id}"]'
            await page.wait_for_selector(cat_selector, timeout=30000)
            await page.locator(cat_selector).first.click()
            await asyncio.sleep(5)
            
            # Espansione lista
            while True:
                btn = page.locator("#btn-loadMore")
                if await btn.is_visible(): await btn.click(); await asyncio.sleep(4)
                else: break
            
            # Correzione qui: attesa corretta dei locator
            await page.wait_for_load_state("networkidle")
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                await page.goto(full_url, timeout=60000)
                try: nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                except: nome_torneo = "Torneo senza nome"
                
                print(f"   [Verifica]: {nome_torneo.strip()}")
                
                dropdown = page.locator("#select-ordergame")
                download_btn = page.locator("#btnOrderGameDownload")
                
                if await dropdown.is_visible():
                    for i in range(0, 2):
                        data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                        if await page.locator(f"#select-ordergame option:has-text('{data_target}')").count() > 0:
                            await page.select_option("#select-ordergame", label=data_target)
                            await asyncio.sleep(3)
                            if await download_btn.is_visible():
                                async with page.expect_download() as dl_info: await download_btn.click()
                                matches = get_pdf_info_filtered((await dl_info.value).path())
                                if matches:
                                    json_data["tornei"].append({"url": full_url, "nomeTorneo": nome_torneo.strip(), "data": data_target, "partite": [format_line_for_swift(m, data_target) for m in matches]})
                
                elif await download_btn.is_visible():
                    async with page.expect_download() as dl_info: await download_btn.click()
                    matches = get_pdf_info_filtered((await dl_info.value).path())
                    if matches:
                        json_data["tornei"].append({"url": full_url, "nomeTorneo": nome_torneo.strip(), "data": "Oggi", "partite": [format_line_for_swift(m, "Oggi") for m in matches]})

            with open(filename, "w", encoding="utf-8") as f: json.dump(json_data, f, ensure_ascii=False, indent=4)
            await page.close()
        await browser.close()
    print("--- [END] Processo completato correttamente ---")

if __name__ == "__main__": asyncio.run(run_bot())
