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
    """
    Formatta la riga in modo pulito: Data; Ora; Categoria; Giocatore 1; Giocatore 2
    """
    # 1. Estrae l'orario
    match_time = re.search(r"(\d{2}:\d{2})", raw_text)
    time = match_time.group(1) if match_time else "00:00"
    
    # 2. Sostituisce il "vs" con "; " per separare i giocatori
    clean_text = re.sub(r"\s+vs\s+", "; ", raw_text, flags=re.IGNORECASE)
    
    # 3. Pulisce l'orario dal testo (lo abbiamo già isolato)
    clean_text = re.sub(r"Inizio ore:\s*\d{2}:\d{2}", "", clean_text).strip()
    
    # 4. Tenta di estrarre la categoria se presente
    cat_keywords = ["Singolare", "Doppio", "Maschile", "Femminile", "Open", "Under", "LIM."]
    found_cat = ""
    for kw in cat_keywords:
        if kw in clean_text:
            # Prende la parte iniziale che contiene la descrizione categoria
            # Questa è un'euristica: cerca di fermarsi prima del primo nome maiuscolo lungo
            parts = re.split(r'\s+(?=[A-Z]{3,})', clean_text, maxsplit=1)
            found_cat = parts[0].strip()
            # Se la parte 0 è troppo lunga o non contiene la categoria, usiamo tutto
            if len(found_cat) > 50: found_cat = "Categoria non specificata"
            break
            
    if not found_cat: found_cat = "N/A"
    
    # Rimuove la categoria dal resto della riga per evitare duplicati
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
                            if cell and "Inizio ore" in cell:
                                matches.append(cell.replace("\n", " ").strip())
    except: pass
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
            
            # Setup filtri
            await page.select_option("#select_status", label="In corso")
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(3)
            
            # Carica tutti i tornei
            while await page.locator("#btn-loadMore").is_visible():
                await page.click("#btn-loadMore")
                await asyncio.sleep(2)
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                for attempt in range(3):
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        
                        # CONTROLLO CRITICO: esiste il menù?
                        if not await page.locator("#select-ordergame").is_visible(timeout=5000):
                            print(f"  -> {full_url}: Menù date non trovato, salto.", flush=True)
                            break
                        
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
                            nome, matches = get_pdf_info(path)
                            
                            if matches:
                                save_data(filename, f">> {nome} ({data_target})")
                                for m in matches:
                                    save_data(filename, format_line_for_swift(m, data_target))
                            if os.path.exists(path): os.remove(path)
                        break 
                    except Exception as e:
                        if attempt < 2: await asyncio.sleep(3)
                        else: print(f"  -> [X] Errore su {full_url}", flush=True)
            await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
