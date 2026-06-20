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
    Formatta la stringa per Swift: Data; Ora; Categoria; Match
    """
    # 1. Estrae l'orario (prende solo il primo orario trovato)
    match_time = re.search(r"Inizio ore:\s*(\d{2}:\d{2})", raw_text)
    time = match_time.group(1) if match_time else "00:00"
    
    # 2. Pulisce il testo rimuovendo "Inizio ore: XX:XX"
    clean_text = re.sub(r"Inizio ore:\s*\d{2}:\d{2}", "", raw_text).strip()
    
    # 3. Separa Categoria e Match
    # Cerca il pattern "Under X" per separare la categoria dal resto
    split_match = re.split(r'(Under \d+\w?)', clean_text, maxsplit=1)
    
    if len(split_match) > 1:
        category = (split_match[0] + split_match[1]).strip()
        match = split_match[2].strip()
    else:
        category = "N/A"
        match = clean_text
        
    return f"{date_target}; {time}; {category}; {match}"

def get_pdf_info(pdf_path):
    """Estrae il titolo del torneo e i match dalla tabella."""
    title = "Torneo FITP"
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Estrarre titolo dalla prima pagina
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            if text:
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if lines:
                    title = lines[0]
            
            # Estrarre dati tabella
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        for cell in row:
                            if cell and "Inizio ore" in cell:
                                # Pulizia basica per evitare duplicati orari nella riga
                                clean_line = cell.replace("\n", " ").strip()
                                matches.append(clean_line)
    except Exception as e:
        print(f"     [!] Errore parsing PDF: {e}", flush=True)
    return title, matches

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n--- Inizio sessione: {filename} ---", flush=True)
            # Sovrascrive il file ad ogni inizio
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Report aggiornato al {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")

            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="networkidle")
            
            await page.select_option("#select_status", label="In corso")
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await page.wait_for_timeout(3000)
            
            while True:
                btn = page.locator("#btn-loadMore")
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(2)
                else:
                    break
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            print(f"[*] Trovati {len(links)} tornei.", flush=True)
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                
                # Logica di Riprova (3 tentativi)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        await page.wait_for_selector("#select-ordergame", timeout=15000)
                        
                        print(f"  -> Elaborando torneo...", flush=True)
                        
                        for i in range(2):
                            data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                            
                            options = await page.locator("#select-ordergame option").all_text_contents()
                            if data_target not in "".join(options):
                                continue 
                                
                            await page.select_option("#select-ordergame", label=data_target)
                            await page.wait_for_timeout(2000)
                            
                            async with page.expect_download(timeout=10000) as dl_info:
                                await page.click("#btnOrderGameDownload")
                            
                            dl = await dl_info.value
                            path = "temp.pdf"
                            await dl.save_as(path)
                            
                            # Estrazione dati e titolo dal PDF
                            nome_torneo, matches = get_pdf_info(path)
                            
                            if matches:
                                save_data(filename, f">> {nome_torneo} ({data_target})")
                                for m in matches:
                                    # Formattazione per Swift
                                    swift_line = format_line_for_swift(m, data_target)
                                    save_data(filename, swift_line)
                                print(f"     [OK] {data_target}: {nome_torneo}", flush=True)
                            
                            if os.path.exists(path): os.remove(path)
                        
                        # Se ha successo, esci dal ciclo di riprova
                        break 
                        
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"     [!] Errore, riprovo {attempt+1}/{max_retries}...", flush=True)
                            await asyncio.sleep(3)
                        else:
                            print(f"     [X] Fallito dopo 3 tentativi.", flush=True)
            
            await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
