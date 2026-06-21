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
        # Cerchiamo la sezione, aspettiamo un minimo
        if await page.locator(".cc-section-participants").count() > 0:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            nomi = await page.locator(".cc-section-participants .cc-name").all_text_contents()
            lista_pulita = [n.strip() for n in nomi if n.strip()]
            if lista_pulita:
                return list(set(lista_pulita))
    except Exception as e:
        print(f"    DEBUG: Errore estrazione iscritti: {e}", flush=True)
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
        start_date_filter = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n--- Inizio sessione: {filename} ---", flush=True)
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}

            for status in STATUSES:
                page = await context.new_page()
                await page.goto(BASE_URL, wait_until="networkidle")
                
                # Selezione filtri
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
                
                # Caricamento elenco tornei
                while await page.locator("#btn-loadMore").is_visible():
                    await page.click("#btn-loadMore")
                    await asyncio.sleep(2)
                
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    print(f"    -> Entro nel torneo: {full_url}", flush=True)
                    
                    try:
                        # ANDIAMO NELLA PAGINA GENERALE DEL TORNEO
                        await page.goto(full_url, wait_until="networkidle")
                        
                        # RECUPERO TUTTI I LINK "DETTAGLIO" DELLE CATEGORIE
                        # Cerchiamo tutti i bottoni 'Dettaglio'
                        dettaglio_links = await page.locator("a:has-text('Dettaglio')").all()
                        urls_categorie = []
                        for d in dettaglio_links:
                            href = await d.get_attribute("href")
                            urls_categorie.append(f"https://www.fitp.it{href}")
                        
                        # Se non trova sottocategorie, usiamo l'url corrente
                        if not urls_categorie: urls_categorie = [full_url]
                        
                        # ITERIAMO SU OGNI CATEGORIA TROVATA
                        for sub_url in urls_categorie:
                            await page.goto(sub_url, wait_until="networkidle")
                            
                            # 1. Nome categoria per il report
                            title_el = page.locator("h1.cc-title-main")
                            nome_cat = await title_el.text_content() if await title_el.count() > 0 else "Categoria ignota"
                            
                            # 2. Estraggo Iscritti
                            if cat_id == "t_giovanili":
                                lista_iscritti = await estrai_iscritti(page)
                                if lista_iscritti:
                                    iscritti_report["tornei"].append({"torneo": nome_cat.strip(), "iscritti": lista_iscritti})
                            
                            # 3. Estraggo Date/Partite (logica PDF)
                            if await page.locator("#select-ordergame").is_visible(timeout=3000):
                                for i in range(2):
                                    data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                                    options = await page.locator("#select-ordergame option").all_text_contents()
                                    if data_target not in "".join(options): continue
                                    
                                    await page.select_option("#select-ordergame", label=data_target)
                                    await asyncio.sleep(2)
                                    async with page.expect_download(timeout=10000) as dl_info:
                                        await page.click("#btnOrderGameDownload")
                                    
                                    path = "temp.pdf"
                                    await (await dl_info.value).save_as(path)
                                    matches = get_pdf_info(path)
                                    # ... (logica salvataggio date invariata)
                                    if os.path.exists(path): os.remove(path)

                    except Exception as e: 
                        print(f"    !! Errore su {full_url}: {e}", flush=True)
                await page.close()
            
            # Salvataggio file
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
        
        with open(ISCRITTI_FILE, "w", encoding="utf-8") as f:
            json.dump(iscritti_report, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print(f"--- Bot completato ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
