import asyncio
import os
import pdfplumber
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {"t_giovanili": "Giovanili_Partite.txt", "t_affiliati": "Open_Partite.txt"}

def save_data(filename, content):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(content + "\n")

def parse_pdf_table(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        for cell in row:
                            if cell and "Inizio ore" in cell:
                                clean_line = cell.replace("\n", " ").strip()
                                matches.append(clean_line)
    except Exception as e:
        print(f"     [!] Errore parsing PDF: {e}", flush=True)
    return matches

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
                
                # --- INIZIO LOGICA RITENTA ---
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        nome = await page.locator("h1").first.inner_text()
                        
                        # Aspetta il menù
                        await page.wait_for_selector("#select-ordergame", timeout=15000)
                        
                        print(f"  -> Elaborando: {nome} (Tentativo {attempt+1})", flush=True)
                        
                        for i in range(2):
                            data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                            
                            # Controlla se la data è selezionabile
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
                            
                            matches = parse_pdf_table(path)
                            if matches:
                                save_data(filename, f">> {nome} ({data_target})")
                                for m in matches:
                                    save_data(filename, f"{data_target}; {m}")
                                print(f"     [OK] {data_target}: Trovati {len(matches)} match.", flush=True)
                            if os.path.exists(path): os.remove(path)
                        
                        # Se arriviamo qui, il torneo è stato processato con successo
                        break 
                        
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"     [!] Errore su {full_url}, riprovo ({attempt+1}/{max_retries})...", flush=True)
                            await asyncio.sleep(3) # Pausa prima di riprovare
                        else:
                            print(f"     [X] Fallito dopo {max_retries} tentativi: {e}", flush=True)
                # --- FINE LOGICA RITENTA ---

            await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
