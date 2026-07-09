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
    "t_giovanili": "Tornei_Date_Giovanili_In_Programma_PDF.json", 
    "t_affiliati": "Tornei_Date_Open_In_Programa_Pdf.json"
}

def format_line_for_swift(raw_text, date_target):
    # 1. Pulisce la riga
    text = raw_text.replace("\n", " ").strip()
    
    # 2. Estrazione orario (HH:MM o HH.MM)
    match_time = re.search(r"(\d{2})[:.](\d{2})", text)
    time = f"{match_time.group(1)}:{match_time.group(2)}" if match_time else "00:00"
    
    # 3. Normalizzazione separatori in " vs "
    # Sostituisce 'o', '/', '|', '-' con ' vs '
    text = re.sub(r"\s+[o/|\-]\s+", " vs ", text, flags=re.IGNORECASE)
    
    # 4. Rimuove orario ripetuto all'inizio se presente
    text = re.sub(r"^\d{2}[:.]\d{2}\s*", "", text)
    
    # 5. Pulizia finale: rimuove spazi doppi
    text = re.sub(r"\s+", " ", text).strip()
    
    # Formato finale garantito: Data; Ora; Giocatore vs Giocatore
    return f"{date_target}; {time}; {text}"

def get_pdf_info(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Scansiona le tabelle cella per cella
                for table in page.extract_tables():
                    for row in table:
                        # Filtra celle che contengono match o riferimenti di gioco
                        cleaned_row = [str(c).strip() for c in row if c and ("vs" in str(c).lower() or " o " in str(c).lower())]
                        if cleaned_row:
                            matches.append(" ".join(cleaned_row))
    except Exception as e:
        print(f"Errore lettura PDF: {e}")
    return matches

async def run_bot():
    print(f"--- Avvio Bot (In Programma) alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            await page.goto(BASE_URL, wait_until="networkidle")
            await page.click('button[data-id="select_status"]')
            await page.locator('span:text-is("In programma")').last.click()
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(5)
            
            while True:
                btn = page.locator("button#btn-loadMore")
                if await btn.is_visible(): 
                    await btn.click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                else: break
            
            urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
            
            for url in urls:
                full_url = f"https://www.fitp.it{url}"
                try:
                    await page.goto(full_url, wait_until="networkidle")
                    if not await page.locator("#select-ordergame").is_visible(timeout=5000): continue
                    
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
                                path = f"temp_{cat_id}_{i}.pdf"
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
