import asyncio
import os
import pdfplumber
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {"t_giovanili": "Giovanili_Partite.txt", "t_affiliati": "Open_Partite.txt"}

def save_data(filename, content):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(content + "\n")

def format_line_for_swift(raw_text, date_target):
    # 1. Estrae l'orario (cerca sia "Inizio ore" che "Non prima delle")
    match_time = re.search(r"(Inizio ore|Non prima delle):\s*(\d{2}:\d{2})", raw_text)
    time = match_time.group(2) if match_time else "00:00"
    
    # 2. Sostituisce "vs" con "; " per separare i giocatori
    clean_text = re.sub(r"\s+vs\s+", "; ", raw_text, flags=re.IGNORECASE)
    
    # 3. Rimuove le indicazioni testuali dell'orario
    clean_text = re.sub(r"(Inizio ore|Non prima delle):\s*\d{2}:\d{2}", "", clean_text).strip()
    
    # 4. Estrazione Categoria
    cat_keywords = ["Singolare", "Doppio", "Maschile", "Femminile", "Open", "Under", "LIM."]
    found_cat = "N/A"
    for kw in cat_keywords:
        if kw in clean_text:
            parts = re.split(r'\s+(?=[A-Z]{3,})', clean_text, maxsplit=1)
            found_cat = parts[0].strip()
            if len(found_cat) > 50: found_cat = "Categoria non specificata"
            break
            
    final_match_data = clean_text.replace(found_cat, "").strip()
    
    return f"{date_target}; {time}; {found_cat}; {final_match_data}"

def get_pdf_info(pdf_path):
    title = "Torneo FITP"
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            if text:
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if lines: title = lines[0]
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        for cell in row:
                            if cell and ("Inizio ore" in cell or "Non prima delle" in cell):
                                matches.append(cell.replace("\n", " ").strip())
    except: 
        pass
    return title, matches

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n--- Inizio sessione: {filename} ---", flush=True)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Report aggiornato al {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")

            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # --- APPLICAZIONE FILTRI ---
            # Filtro 1: Stato
            await page.select_option("#select_status", label="In corso")
            await asyncio.sleep(2) 
            
            # Filtro 2: Regione Lazio
            await page.click('button[data-id="id_regioneSearch"]')
            await asyncio.sleep(1)
            await page.get_by_role("option", name="Lazio").click()
            await asyncio.sleep(2) 
            
            # Filtro 3: Categoria
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(3) 
            
            # Caricamento lista
            while await page.locator("#btn-loadMore").is_visible():
                await page.click("#btn-loadMore")
                await asyncio.sleep(2)
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            
            print(f"[*] Trovati {len(links)} tornei filtrati. Inizio estrazione...", flush=True)
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                for attempt in range(2): 
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        if not await page.locator("#select-ordergame").is_visible(timeout=5000):
                            break
                        
                        for i in range(2):
                            data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                            options = await page.locator("#select-ordergame option").all_text_contents()
                            if data_target not in "".join(options): 
                                continue 
                                
                            await page.select_option("#select-ordergame", label=data_target)
                            await asyncio.sleep(2)
                            
                            async with page.expect_download(timeout=10000) as dl_info:
                                await page.click("#btnOrderGameDownload")
                            
                            path = "temp.pdf"
                            await (await dl_info.value).save_as(path)
                            nome, matches = get_pdf_info(path)
                            
                            if matches:
                                save_data(filename, f">> {nome} ({data_target})")
                                for m in matches:
                                    save_data(filename, format_line_for_swift(m, date_target=data_target))
                            if os.path.exists(path): 
                                os.remove(path)
                        break 
                    except Exception:
                        await asyncio.sleep(2)
            await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
