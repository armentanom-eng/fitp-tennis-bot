import asyncio
import os
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {"t_giovanili": "Giovanili_Tornei.json"} # Usiamo solo giovanili come da tua richiesta
STATUSES = ["In corso", "Iscrizioni aperte"]
OUTPUT_FILE = "Tornei_e_Iscritti.json"

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

async def estrai_iscritti_u14(page):
    """Cerca la riga Singolare Femminile Under 14, entra nel dettaglio ed estrae i nomi"""
    try:
        print("    DEBUG: Cerco riga categoria 'Singolare Femminile Under 14'...", flush=True)
        # Cerchiamo la riga che contiene la categoria (anche con testo aggiuntivo) e clicchiamo Dettaglio
        target_row = page.locator("tr").filter(has_text=re.compile("Singolare Femminile Under 14", re.IGNORECASE))
        
        if await target_row.count() > 0:
            print("    DEBUG: Categoria trovata, entro nel dettaglio...", flush=True)
            await target_row.get_by_role("link", name="Dettaglio").click()
            await page.wait_for_load_state("networkidle")
            
            # Estrazione nomi (assumendo classe .cc-name come da screenshot)
            nomi = await page.locator(".cc-name").all_text_contents()
            lista_pulita = [n.strip() for n in nomi if n.strip()]
            
            await page.go_back()
            await page.wait_for_load_state("networkidle")
            return lista_pulita
        else:
            print("    DEBUG: Categoria Under 14 non presente in questo torneo.", flush=True)
            return None
    except Exception as e:
        print(f"    ! Errore estrazione iscritti: {e}", flush=True)
        return None

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    dati_finali = {} # Struttura: { "Nome Torneo": ["Giocatore 1", "Giocatore 2"] }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        start_date_filter = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        
        for status in STATUSES:
            print(f"\n--- Inizio sessione: Stato '{status}' ---", flush=True)
            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Filtri
            await page.click('button[data-id="select_status"]')
            await asyncio.sleep(1)
            await page.get_by_role("listbox").get_by_role("option", name=status).click()
            await asyncio.sleep(1)
            
            # Filtro Regione
            await page.click('button[data-id="id_regioneSearch"]')
            await asyncio.sleep(1)
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(1)
            
            # Filtro Provincia
            await page.click('button[data-id="id_provinciaSearch"]')
            await asyncio.sleep(1)
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(1)
            
            await page.fill("#dpk_start_date", start_date_filter)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(2)
            
            # Categoria Giovanili
            await page.locator('a[data-id="t_giovanili"]').first.click()
            await asyncio.sleep(3) 
            
            # Carica altri
            while await page.locator("#btn-loadMore").is_visible():
                print("    Caricamento altri risultati...", flush=True)
                await page.click("#btn-loadMore")
                await asyncio.sleep(2)
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            print(f"    Trovati {len(links)} tornei.", flush=True)
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                try:
                    await page.goto(full_url, wait_until="networkidle")
                    title_el = page.locator("h1.cc-title-main.spn-competition-description")
                    nome_torneo = (await title_el.text_content()).strip() if await title_el.count() > 0 else "Torneo sconosciuto"
                    
                    print(f"    -> Analizzo torneo: {nome_torneo} | Link: {full_url}", flush=True)
                    
                    iscritti = await estrai_iscritti_u14(page)
                    if iscritti:
                        dati_finali[nome_torneo] = iscritti
                        print(f"       [OK] Trovati {len(iscritti)} iscritti.", flush=True)
                    else:
                        print("       [Info] Nessun iscritto trovato per la categoria richiesta.", flush=True)
                        
                except Exception as e: 
                    print(f"    !! Errore su {full_url}: {e}", flush=True)
            
            await page.close()
            
        # Salvataggio unico
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dati_finali, f, ensure_ascii=False, indent=4)
            print(f"\n--- [OK] File {OUTPUT_FILE} salvato con successo. ---", flush=True)
            
        await browser.close()
        print(f"--- Bot completato ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
