import asyncio
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# --- CONFIGURAZIONE FACILE ---
FILTERS = {
    "stato": "In programma",
    "regione": "Lazio",
    "provincia": "Roma"
}

CATEGORIES = {
    "t_giovanili": "Tornei_Giovanili_Custom.json", 
    "t_affiliati": "Tornei_Open_Custom.json"
}
# -----------------------------

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
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True, viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")

        # Applicazione filtri
        for selector, key in [('button[data-id="select_status"]', "stato"), 
                               ('button[data-id="id_regioneSearch"]', "regione"), 
                               ('button[data-id="id_provinciaSearch"]', "provincia")]:
            await page.click(selector)
            option = page.get_by_role("option", name=FILTERS[key])
            await option.wait_for(state="visible")
            await option.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

        for cat_id, filename in CATEGORIES.items():
            print(f">>> Elaborazione: {cat_id} -> {filename}")
            json_data = {"data_aggiornamento": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            
            await page.locator(f'a[data-id="{cat_id}"]').click()
            await page.wait_for_load_state("networkidle")
            
            # Espansione lista
            while await page.locator("#btn-loadMore").is_visible():
                await page.locator("#btn-loadMore").click()
                await asyncio.sleep(2)
            
            links = await page.locator("a[href*='Dettaglio-Competizione']").evaluate_all("els => els.map(a => a.getAttribute('href'))")
            
            for link in list(set(links)):
                await page.goto(f"https://www.fitp.it{link}", wait_until="networkidle")
                nome_torneo = await page.locator("h1.cc-title-main").inner_text()
                
                # Logica PDF
                download_btn = page.locator("#btnOrderGameDownload")
                if await download_btn.is_visible():
                    async with page.expect_download() as dl_info:
                        await download_btn.click()
                    download = await dl_info.value
                    await download.save_as("temp.pdf")
                    matches = get_pdf_info("temp.pdf")
                    json_data["tornei"].append({
                        "nome": nome_torneo.strip(),
                        "partite": [format_line_for_swift(m, "Oggi") for m in matches]
                    })
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
        
        await browser.close()
    print("--- [END] Processo terminato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
