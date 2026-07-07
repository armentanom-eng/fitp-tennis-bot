import asyncio
import os
import pdfplumber
import re
import json
import logging
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {
    "t_giovanili": "Giovanili_Tornei.json", 
    "t_affiliati": "Open_Tornei.json"
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

async def get_iscritti(page):
    iscritti = []
    try:
        await page.wait_for_selector("span.cc-name", timeout=3000)
        elementi = await page.locator("span.cc-name").all_text_contents()
        iscritti = [nome.strip() for nome in elementi if nome.strip()]
    except:
        logger.warning("Nessun iscritto trovato per questa categoria.")
    return iscritti

async def run_bot():
    logger.info("--- Avvio del Bot di estrazione ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        start_date_filter = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        
        for cat_id, filename in CATEGORIES.items():
            logger.info(f"--- Inizio elaborazione categoria: {cat_id} ---")
            json_data = {"data_estrazione": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}

            for status in STATUSES:
                logger.info(f"Applicazione filtri: {status}, Regione Lazio, Data > {start_date_filter}")
                page = await context.new_page()
                await page.goto(BASE_URL, wait_until="networkidle")
                
                # Applicazione filtri
                await page.click('button[data-id="select_status"]')
                await page.get_by_role("listbox").get_by_role("option", name=status).click()
                await page.click('button[data-id="id_regioneSearch"]')
                await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
                await page.fill("#dpk_start_date", start_date_filter)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                
                # Selezione tipologia torneo (Giovanili/Open)
                await page.locator(f'a[data-id="{cat_id}"]').first.click()
                await asyncio.sleep(3)
                
                while await page.locator("#btn-loadMore").is_visible():
                    logger.info("Caricamento altri risultati...")
                    await page.click("#btn-loadMore")
                    await asyncio.sleep(2)
                
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                logger.info(f"Trovati {len(links)} tornei per {status}.")
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        nome_torneo = await page.locator("h1.cc-title-main").text_content()
                        logger.info(f"Analisi torneo: {nome_torneo.strip()}")
                        
                        torneo_entry = {"nome": nome_torneo.strip(), "url": full_url, "iscritti": {}, "partite": []}
                        
                        # 1. Estrarre iscritti dalle Tab
                        tabs = await page.locator(".nav-link").all()
                        for tab in tabs:
                            nome_tab = (await tab.text_content()).strip()
                            await tab.click()
                            await asyncio.sleep(1.5)
                            torneo_entry["iscritti"][nome_tab] = await get_iscritti(page)
                            logger.info(f"  -> Estratti iscritti tab: {nome_tab}")

                        # 2. Estrarre Partite
                        if await page.locator("#select-ordergame").is_visible(timeout=2000):
                            async with page.expect_download() as dl_info:
                                await page.click("#btnOrderGameDownload")
                            path = "temp.pdf"
                            await (await dl_info.value).save_as(path)
                            torneo_entry["partite"] = get_pdf_info(path)
                            if os.path.exists(path): os.remove(path)
                            
                        json_data["tornei"].append(torneo_entry)
                    except Exception as e:
                        logger.error(f"Errore durante analisi torneo {full_url}: {e}")
                
                await page.close()

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            logger.info(f"--- Salvataggio completato: {filename} ---")
            
        await browser.close()
        logger.info("Bot terminato con successo.")

if __name__ == "__main__":
    asyncio.run(run_bot())
