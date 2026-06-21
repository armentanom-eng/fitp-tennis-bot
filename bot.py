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

# --- FUNZIONE INTEGRATA DI ESTRAZIONE ---
async def estrai_iscritti(page):
    try:
        # Attendiamo il caricamento della sezione
        if await page.locator(".cc-section-participants").count() > 0:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            nomi = await page.locator(".cc-name").all_text_contents()
            lista_pulita = [n.strip() for n in nomi if n.strip()]
            print(f"     -> [ISCRITTI] Trovati {len(lista_pulita)} atleti.", flush=True)
            return list(set(lista_pulita))
    except Exception as e:
        print(f"    ! Errore estrazione iscritti: {e}", flush=True)
    return []

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

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        start_date_filter = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n--- Inizio sessione: {filename} ---", flush=True)
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}

            for status in STATUSES:
                print(f"  -> Elaborazione stato: {status}...", flush=True)
                page = await context.new_page()
                await page.goto(BASE_URL, wait_until="networkidle")
                
                await page.click('button[data-id="select_status"]')
                await asyncio.sleep(1)
                await page.get_by_role("listbox").get_by_role("option", name=status).click()
                await asyncio.sleep(1)
                await page.click('button[data-id="id_regioneSearch"]')
                await asyncio.sleep(1)
                await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
                await asyncio.sleep(1)
                await page.fill("#dpk_start_date", start_date_filter)
                await page.keyboard.press("Enter") 
                await asyncio.sleep(2)
                await page.locator(f'a[data-id="{cat_id}"]').first.click()
                await asyncio.sleep(3) 
                
                while await page.locator("#btn-loadMore").is_visible():
                    print("     Caricamento altri risultati...", flush=True)
                    await page.click("#btn-loadMore")
                    await asyncio.sleep(2)
                
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
                
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                print(f"     Trovati {len(links)} tornei.", flush=True)
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    torneo_entry = {"nome": "In caricamento...", "url": full_url, "date": [], "iscritti": []}
                    json_data["tornei"].append(torneo_entry)
                    
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        
                        # --- INTEGRAZIONE: Clicco nella categoria desiderata ---
                        # Cerchiamo il blocco che contiene "Singolare Femminile Under 14"
                        # e clicchiamo il suo link "Dettaglio"
                        cat_locator = page.locator(".cc-single-tournament").filter(has_text="Singolare Femminile Under 14").get_by_role("link", name="Dettaglio")
                        
                        if await cat_locator.count() > 0:
                            print("     -> Categoria trovata, entro...", flush=True)
                            await cat_locator.click()
                            await page.wait_for_load_state("networkidle")
                            
                            # Estraggo anche gli iscritti
                            torneo_entry["iscritti"] = await estrai_iscritti(page)
                        else:
                            print("     -> Categoria 'Singolare Femminile Under 14' non presente, salto PDF.", flush=True)
                            continue # Salta la parte PDF se non trova la categoria
                        
                        # --- FINE INTEGRAZIONE ---

                        # --- FIX TITOLO ---
                        title_el = page.locator("h1.cc-title-main.spn-competition-description")
                        if await title_el.count() > 0:
                            nome = await title_el.text_content()
                            torneo_entry["nome"] = nome.strip()
                        
                        print(f"     -> Analizzo: {torneo_entry['nome']}", flush=True)

                        if not await page.locator("#select-ordergame").is_visible(timeout=3000):
