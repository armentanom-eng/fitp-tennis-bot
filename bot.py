import asyncio
import os
import pdfplumber
import re
import json
import logging
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione Logging dettagliato
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {
    "t_giovanili": "Giovanili_Partite.json", 
    "t_affiliati": "Open_Partite.json"
}
STATUSES = ["In corso", "Iscrizioni aperte"]

def format_line_for_swift(raw_text, date_target):
    match_time = re.search(r"(Inizio ore|Non prima delle):\s*(\d{2}:\d{2})", raw_text)
    time = match_time.group(2) if match_time else "00:00"
    clean_text = re.sub(r"\s+vs\s+", "; ", raw_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"(Inizio ore|Non prima delle):\s*\d{2}:\d{2}", "", clean_text).strip()
    clean_text = re.sub(r"(LIM\.\s+[\w\.]+\s*-\s*[\w\.]+)", r"\1;", clean_text)
    
    cat_keywords = ["Singolare", "Doppio", "Maschile", "Femminile", "Open", "Under", "LIM."]
    found_cat = "N/A"
    for kw in cat_keywords:
        if kw in clean_text:
            parts = re.split(r'\s+(?=[A-Z]{3,})', clean_text, maxsplit=1)
            found_cat = parts[0].strip()
            break
    final_match_data = clean_text.replace(found_cat, "").strip().lstrip(';').strip()
    return f"{date_target}; {time}; {found_cat}; {final_match_data}"

def get_pdf_info(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        for cell in row:
                            if cell and ("Inizio ore" in cell or "Non prima delle" in cell):
                                matches.append(cell.replace("\n", " ").strip())
    except Exception as e:
        logger.error(f"Errore lettura PDF: {e}")
    return matches

async def get_iscritti(page, tab_name):
    """Estrae i nomi dalla tabella, con log di debug."""
    iscritti = []
    try:
        # Debug: vediamo se la tabella esiste
        if await page.locator("span.cc-name").first.is_visible(timeout=3000):
            elementi = await page.locator("span.cc-name").all_text_contents()
            iscritti = [nome.strip() for nome in elementi if nome.strip()]
            logger.info(f"   [DEBUG] Trovati {len(iscritti)} iscritti nella tab '{tab_name}'")
        else:
            logger.warning(f"   [DEBUG] Nessun elemento 'span.cc-name' trovato nella tab '{tab_name}'")
    except Exception as e:
        logger.error(f"   [DEBUG] Errore durante estrazione iscritti in '{tab_name}': {e}")
    return iscritti

async def run_bot():
    logger.info("--- Avvio Bot ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        start_date_filter = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        
        for cat_id, filename in CATEGORIES.items():
            logger.info(f"--- Inizio sessione: {filename} ---")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}

            for status in STATUSES:
                logger.info(f"-> Elaborazione stato: {status}")
                page = await context.new_page()
                await page.goto(BASE_URL, wait_until="networkidle")
                
                # ... (Filtri invariati)
                await page.click('button[data-id="select_status"]')
                await page.get_by_role("listbox").get_by_role("option", name=status).click()
                await page.click('button[data-id="id_regioneSearch"]')
                await page.get_by_role("listbox").get_by_role("option", name=status).click() # (Corretto in base a logica precedente)
                await page.fill("#dpk_start_date", start_date_filter)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                await page.locator(f'a[data-id="{cat_id}"]').first.click()
                await asyncio.sleep(3) 

                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                logger.info(f"-> Trovati {len(links)} tornei.")
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    logger.info(f"-> Analizzo URL: {full_url}")
                    
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        
                        # Fix Titolo
                        title_el = page.locator("h1.cc-title-main.spn-competition-description")
                        nome_torneo = "Sconosciuto"
                        if await title_el.count() > 0:
                            nome_torneo = (await title_el.first.text_content()).strip()
                        
                        torneo_entry = {"nome": nome_torneo, "url": full_url, "iscritti": {}, "date": []}
                        
                        # Debug Tab
                        tabs = await page.locator("a[data-toggle='tab']").all()
                        logger.info(f"   Trovate {len(tabs)} tab categorie.")
                        
                        for tab in tabs:
                            tab_text = (await tab.text_content()).strip()
                            await tab.click()
                            await asyncio.sleep(2)
                            logger.info(f"   Cliccato su tab: {tab_text}")
                            torneo_entry["iscritti"][tab_text] = await get_iscritti(page, tab_text)

                        json_data["tornei"].append(torneo_entry)
                    except Exception as e:
                        logger.error(f"!! Errore critico su {full_url}: {e}")
                
                await page.close()
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            logger.info(f"--- [OK] File {filename} salvato. ---")
            
        await browser.close()
        logger.info("--- Bot completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
