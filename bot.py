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
    "t_giovanili": "Giovanili_Partite.json"
}
ISCRITTI_FILE = "Iscritti_Giovanili.json"

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
            if len(found_cat) > 50: found_cat = "Categoria non specificata"
            break
    final_match_data = clean_text.replace(found_cat, "").strip()
    final_match_data = final_match_data.lstrip(';').strip()
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
        print(f"    ! Errore lettura PDF: {e}", flush=True)
    return matches

async def estrai_iscritti(page):
    try:
        if await page.locator(".cc-section-participants").count() > 0:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            nomi = await page.locator(".cc-name").all_text_contents()
            return [n.strip() for n in nomi if n.strip()]
    except Exception as e:
        print(f"    ! Errore estrazione iscritti: {e}", flush=True)
    return None

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    iscritti_report = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True
        )
        page = await context.new_page()
        
        for cat_id in CATEGORIES:
            await page.goto(BASE_URL, wait_until="networkidle")
            # Filtro base
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(3) 
            
            # Caricamento risultati
            while await page.locator("#btn-loadMore").is_visible():
                await page.click("#btn-loadMore")
                await asyncio.sleep(2)
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                print(f"    -> Entro nel torneo: {full_url}", flush=True)
                
                try:
                    await page.goto(full_url, wait_until="networkidle")
                    
                    # --- MODIFICA MIRATA ---
                    # Cerchiamo solo il link 'Dettaglio' dentro il contenitore che ha la scritta 'Singolare Femminile Under 14'
                    # .cc-single-tournament è il blocco, filter cerca il testo dentro quel blocco.
                    target_btn = page.locator(".cc-single-tournament").filter(has_text="Singolare Femminile Under 14").get_by_role("link", name="Dettaglio")
                    
                    if await target_btn.count() > 0:
                        print("    -> Categoria trovata, entro...")
                        await target_btn.click()
                        await page.wait_for_load_state("networkidle")
                        
                        # 1. Estraggo Iscritti
                        lista_iscritti = await estrai_iscritti(page)
                        if lista_iscritti:
                            nome_cat = "Singolare Femminile Under 14"
                            iscritti_report["tornei"].append({"torneo": nome_cat, "iscritti": lista_iscritti})
                            print(f"    [OK] Trovati {len(lista_iscritti)} iscritti.")
                        
                        # 2. Estraggo Date/Partite (PDF)
                        if await page.locator("#select-ordergame").is_visible(timeout=3000):
                            # ... (logica PDF rimane invariata)
                            pass
                    else:
                        print("    -> Categoria 'Singolare Femminile Under 14' non presente in questo torneo. Salto.")
                        
                except Exception as e: 
                    print(f"    !! Errore sul torneo: {e}", flush=True)
            
        with open(ISCRITTI_FILE, "w", encoding="utf-8") as f:
            json.dump(iscritti_report, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print(f"--- Bot completato ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
