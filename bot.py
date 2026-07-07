import asyncio
import os
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {"t_giovanili": "Giovanili_Partite.json", "t_affiliati": "Open_Partite.json"}
STATUSES = ["In corso", "Iscrizioni aperte"]

def get_target_category():
    # Dal 01/01/2027 passa da Under 14 a Under 16
    if datetime.now() >= datetime(2027, 1, 1):
        return "Under 16"
    return "Under 14"

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
            
    final_match_data = clean_text.replace(found_cat, "").strip().lstrip(';')
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
    except Exception as e: print(f"    ! Errore PDF: {e}")
    return matches

async def run_bot():
    print(f"--- [START] Bot avviato alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(accept_downloads=True, user_agent="Mozilla/5.0")
        
        target_cat = get_target_category()
        print(f"--- Target Categoria Giovanile Corrente: {target_cat} ---")
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Elaborazione Categoria: {filename}")
            json_data = {"report": datetime.now().strftime("%d/%m/%Y"), "tornei": []}
            
            for status in STATUSES:
                page = await context.new_page()
                await page.goto(BASE_URL, wait_until="networkidle")
                
                # Filtri
                await page.click('button[data-id="select_status"]')
                await page.get_by_role("listbox").get_by_role("option", name=status).click()
                await page.click('button[data-id="id_regioneSearch"]')
                await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
                await page.keyboard.press("Enter")
                await asyncio.sleep(5)
                
                # Caricamento infinito
                while await page.locator("button#btn-loadMore").is_visible():
                    print("    -> Caricamento altri tornei...")
                    await page.click("button#btn-loadMore")
                    await page.wait_for_load_state("networkidle")
                
                links = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
                print(f"    -> Trovati {len(links)} tornei per stato '{status}'")
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    await page.goto(full_url, wait_until="networkidle")
                    try: await page.get_by_role("button", name="Accetta").click(timeout=2000)
                    except: pass
                    
                    nome = await page.locator("h1.cc-title-main").first.text_content()
                    print(f"        * Analizzo torneo: {nome.strip()}")
                    
                    # Estrazione Categorie con protezione timeout
                    dettagli = page.locator("text=Dettaglio >")
                    count = await dettagli.count()
                    for i in range(count):
                        try:
                            btn = dettagli.nth(i)
                            if await btn.is_visible(timeout=2000):
                                await btn.click(force=True)
                                await page.wait_for_load_state("networkidle")
                                
                                cat_name = await page.locator("h1.cc-title-main").first.text_content()
                                if target_cat in cat_name:
                                    print(f"            + Trovata categoria target: {cat_name.strip()}")
                                
                                await page.go_back()
                                await page.wait_for_load_state("networkidle")
                        except Exception as e:
                            print(f"            ! Errore su bottone {i}, proseguo...")
                            await page.goto(full_url)
                    
                    # Elaborazione PDF
                    if await page.locator("#select-ordergame").is_visible(timeout=3000):
                        print(f"            + Elaborazione PDF disponibile.")
                        # (Logica PDF esistente...)
                    
                    json_data["tornei"].append({"nome": nome.strip(), "url": full_url})
                await page.close()
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            print(f"--- [OK] Salvato {filename} ---")
            
        await browser.close()
        print("--- [END] Bot completato con successo ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
