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

# Helper per attese dinamiche più precise
async def wait_and_click(page, selector):
    await page.wait_for_selector(selector, state="visible", timeout=20000)
    await page.click(selector)

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
    print("--- [START] Avvio estrazione dinamica ---")
    async with async_playwright() as p:
        # Browser configurato per GitHub Actions
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Filtri dinamici con selettore corretto per evitare strict mode violation
            for sel_id, option in [('select_status', 'In corso'), ('id_regioneSearch', 'Lazio'), ('id_provinciaSearch', 'Roma')]:
                await wait_and_click(page, f'button[data-id="{sel_id}"]')
                
                # Selettore specifico per il menu grafico, ignorando i tag <option> nascosti
                opt = page.locator(f"a[role='option']:has-text('{option}')").first
                await opt.wait_for(state="visible")
                await opt.click()
                await page.wait_for_load_state("networkidle")
            
            # Categoria
            await wait_and_click(page, f'a[data-id="{cat_id}"]')
            await page.wait_for_load_state("networkidle")
            
            # Espansione lista
            while True:
                btn = page.locator("#btn-loadMore")
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_load_state("networkidle")
                else:
                    break
            
            links = await page.locator("a[href*='Dettaglio-Competizione']").all_attribute_values("href")
            links = list(set(links))
            
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            
            for link in links:
                await page.goto(f"https://www.fitp.it{link}", wait_until="networkidle")
                
                nome_torneo = await page.locator("h1.cc-title-main").inner_text(timeout=15000)
                download_btn = page.locator("#btnOrderGameDownload")
                dropdown = page.locator("#select-ordergame")
                
                # Gestione dinamica date
                if await dropdown.is_visible():
                    for i in range(0, 2):
                        data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                        if await page.locator(f"#select-ordergame option:has-text('{data_target}')").count() > 0:
                            await page.select_option("#select-ordergame", label=data_target)
                            await page.wait_for_load_state("networkidle")
                            
                            if await download_btn.is_visible():
                                async with page.expect_download() as dl_info:
                                    await download_btn.click()
                                download = await dl_info.value
                                await download.save_as("temp.pdf")
                                matches = get_pdf_info("temp.pdf")
                                json_data["tornei"].append({"nomeTorneo": nome_torneo, "data": data_target, "partite": [format_line_for_swift(m, data_target) for m in matches]})
                
                elif await download_btn.is_visible():
                    async with page.expect_download() as dl_info:
                        await download_btn.click()
                    download = await dl_info.value
                    await download.save_as("temp.pdf")
                    matches = get_pdf_info("temp.pdf")
                    json_data["tornei"].append({"nomeTorneo": nome_torneo, "data": "Oggi", "partite": [format_line_for_swift(m, "Oggi") for m in matches]})
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            await page.close()
        await browser.close()
    print("--- [END] Processo completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
