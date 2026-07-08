import asyncio
import os
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {
    "t_giovanili": "Giovanili_Partite.json", 
    "t_affiliati": "Open_Partite.json"
}
STATUSES = ["In corso", "Iscrizioni aperte"]

def format_line_for_swift(raw_text, date_target):
    # 1. Estrazione orario
    match_time = re.search(r"(\d{2}:\d{2})", raw_text)
    time = match_time.group(1) if match_time else "00:00"
    
    # 2. Pulizia di base
    text = raw_text.replace("\n", " ").strip()
    
    # 3. Estrazione Categoria e Limiti (es. Open LIM. 4.NC - 3.1)
    # Cerca il blocco della categoria e limiti (es. "Open LIM. 4.NC - 3.1")
    cat_match = re.search(r"(Singolare|Doppio|Maschile|Femminile|Open|Under|Giovanile)?\s*(.*?[\d\.]+\s*[-]\s*[\d\.]+)", text, re.IGNORECASE)
    categoria_limiti = cat_match.group(0).strip() if cat_match else "N/A"
    
    # 4. Estrazione Giocatori: rimuove orario e categoria, poi split sul VS
    giocatori_part = re.sub(r".*?[\d\.]+\s*[-]\s*[\d\.]+\s*", "", text, flags=re.IGNORECASE)
    giocatori_part = re.sub(r"\d{2}:\d{2}", "", giocatori_part)
    giocatori_part = re.sub(r"\s+vs\s+", "; ", giocatori_part, flags=re.IGNORECASE)
    
    # Ritorna formato: Data; Ora; Categoria; Giocatore 1; Giocatore 2
    return f"{date_target}; {time}; {categoria_limiti}; {giocatori_part.strip()}"

def get_pdf_info(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        row_text = " ".join([str(cell) for cell in row if cell])
                        if any(x in row_text for x in ["Inizio", "Non prima", ":"]):
                            matches.append(row_text)
                if not matches:
                    text = page.extract_text()
                    if text:
                        matches.extend([line.strip() for line in text.split('\n') if ":" in line])
    except Exception as e:
        print(f"    ! Errore lettura PDF: {e}")
    return matches

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            for status in STATUSES:
                print(f"--- Sessione: {filename} | Stato: {status} ---", flush=True)
                await page.goto(BASE_URL, wait_until="networkidle")
                await page.click('button[data-id="select_status"]')
                await page.get_by_role("listbox").get_by_role("option", name=status).click()
                await page.click('button[data-id="id_regioneSearch"]')
                await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
                await page.locator(f'a[data-id="{cat_id}"]').first.click()
                await asyncio.sleep(3)
                
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        if not await page.locator("#select-ordergame").is_visible(timeout=5000): 
                            continue
                        
                        for i in range(2):
                            data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                            
                            if await page.locator(f"#select-ordergame option:has-text('{data_target}')").count() > 0:
                                await page.select_option("#select-ordergame", label=data_target)
                                await asyncio.sleep(2)
                                
                                download_btn = page.locator("#btnOrderGameDownload")
                                if await download_btn.is_visible():
                                    async with page.expect_download(timeout=10000) as dl_info:
                                        await download_btn.click()
                                    
                                    download = await dl_info.value
                                    path = f"temp_{i}.pdf"
                                    await download.save_as(path)
                                    
                                    matches = get_pdf_info(path)
                                    if matches:
                                        json_data["tornei"].append({
                                            "url": full_url,
                                            "data": data_target,
                                            "partite": [format_line_for_swift(m, data_target) for m in matches]
                                        })
                                    if os.path.exists(path): os.remove(path)
                    except Exception as e:
                        print(f"    !! Errore su {full_url}: {e}", flush=True)
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            await page.close()
            
        await browser.close()
        print("--- Bot completato ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
