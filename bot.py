import asyncio
import os
import pdfplumber
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {"t_giovanili": "Giovanili_Partite.txt", "t_affiliati": "Open_Partite.txt"}
# Ho aggiunto la lista degli stati da ciclare
STATUSES = ["In corso", "Iscrizioni aperte"]

def save_data(filename, content):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(content + "\n")

def format_line_for_swift(raw_text, date_target):
    match_time = re.search(r"(Inizio ore|Non prima delle):\s*(\d{2}:\d{2})", raw_text)
    time = match_time.group(2) if match_time else "00:00"
    clean_text = re.sub(r"\s+vs\s+", "; ", raw_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"(Inizio ore|Non prima delle):\s*\d{2}:\d{2}", "", clean_text).strip()
    
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
    except Exception as e:
        print(f"    ! Errore lettura PDF: {e}")
    return title, matches

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n--- Inizio sessione: {filename} ---", flush=True)
            # Scrittura iniziale (sovrascrive solo all'inizio della categoria)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Report aggiornato al {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")

            # Ciclo sugli stati (In corso -> Iscrizioni aperte)
            for status in STATUSES:
                print(f"  -> Elaborando stato: {status}", flush=True)
                
                page = await context.new_page()
                await page.goto(BASE_URL, wait_until="networkidle")
                
                # Applicazione filtri
                await page.select_option("#select_status", label=status)
                await asyncio.sleep(2) 
                await page.click('button[data-id="id_regioneSearch"]')
                await asyncio.sleep(1)
                await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
                await asyncio.sleep(2) 
                await page.locator(f'a[data-id="{cat_id}"]').first.click()
                await asyncio.sleep(3) 
                
                # Caricamento progressivo (Carica altri...)
                while await page.locator("#btn-loadMore").is_visible():
                    await page.click("#btn-loadMore")
                    await asyncio.sleep(2)
                
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                
                print(f"[*] Trovati {len(links)} tornei per '{status}'. Inizio estrazione...", flush=True)
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        # Se è "Iscrizioni aperte", probabilmente non ci sono ancora orari/PDF
                        if not await page.locator("#select-ordergame").is_visible(timeout=3000):
                            print(f"    - Nessun orario/PDF trovato per: {full_url.split('/')[-1]}")
                            continue
                        
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
                            
                            if os.path.exists(path): os.remove(path)
                            
                    except Exception as e:
                        print(f"    !! Errore su {full_url}: {e}")
                
                await page.close()
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
