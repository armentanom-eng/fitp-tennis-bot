import asyncio
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

# Nomi dei file
CATEGORIES = {
    "t_giovanili": "Giovanili_Partite_incorsopdf.json", 
    "t_affiliati": "Open_Partite_incorsopdf.json"
}
STATUSES = ["In corso"]

def format_line_for_swift(raw_text, date_target):
    text = raw_text.replace("\n", " ").strip()
    match_time = re.search(r"(\d{2})[:.](\d{2})", text)
    time = f"{match_time.group(1)}:{match_time.group(2)}" if match_time else "00:00"
    text = re.sub(r"(INIZIO|ORE|NON PRIMA DI|TABELLONE)?[:\s]*\d{2}[:.](\d{2})", "", text, flags=re.IGNORECASE)
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
    print("--- [START] Avvio estrazione PROGRAMMI GARE (da 30 giorni prima di domani fino a dopodomani) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Processo categoria: {cat_id}")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            await page.goto(BASE_URL, timeout=60000)
            
            # Filtro Stato
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name="In corso").click()
            await asyncio.sleep(3)
            
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(3)
            
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(3)
            
            # Selezione Categoria con attesa robusta
            print(f"-> Attendendo categoria {cat_id}...")
            cat_selector = f'a[data-id="{cat_id}"]'
            await page.wait_for_selector(cat_selector, timeout=30000)
            await page.locator(cat_selector).first.click()
            await asyncio.sleep(6)
            
            # Espansione lista
            print("-> Espansione lista tornei...")
            while True:
                btn_load_more = page.locator("#btn-loadMore")
                if await btn_load_more.is_visible():
                    await btn_load_more.click()
                    await asyncio.sleep(6)
                else:
                    break
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            print(f"-> Trovati {len(links)} tornei. Inizio analisi...")
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                await page.goto(full_url, timeout=60000)
                
                try:
                    nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                except:
                    nome_torneo = "Torneo senza nome"
                
                print(f"   [Analizzo]: {nome_torneo.strip()}")
                
                dropdown_selector = "#select-ordergame"
                download_btn = page.locator("#btnOrderGameDownload")
                
                if await page.locator(dropdown_selector).is_visible():
                    # Riferimenti temporali: da 30 giorni prima di domani fino a dopodomani
                    oggi = datetime.now()
