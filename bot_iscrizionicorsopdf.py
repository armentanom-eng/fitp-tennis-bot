import asyncio
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

# Nomi dei file
CATEGORIES = {
    "t_giovanili": "Giovanili_Partite_incorsopdf.json", 
    "t_affiliati": "Open_Partite_incorsopdf.json"
}
STATUSES = ["In corso"]

def format_line_for_swift(raw_text, date_target):
    text = raw_text.replace("\n", " ").strip()
    match_time = re.search(r"(\d{2})[:.](\d{2})", text)
    time = f"{match_time.group(1)}:{match_time.group(2)}" if match_time else "00:00"
    text = re.sub(r"(INIZIO|ORE|NON PRIMA DI|TABELLONE)?[:\s]*\d{2}[:.](\d{2})", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+o\s+", " vs ", text, flags=re.IGNORECASE)
    partite = re.findall(r"([A-Z\s\d\(\)]+?)\s+vs\s+([A-Z\s\d\(\)]+)", text)
    if partite:
        clean = [f"{p[0].strip()} vs {p[1].strip()}" for p in partite]
        return f"{date_target}; {time}; {'; '.join(clean)}"
    return f"{date_target}; {time}; {text.strip()}"

def get_pdf_info(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        row_text = " ".join([str(cell).strip() for cell in row if cell])
                        if len(row_text) > 5: matches.append(row_text)
    except: pass
    return matches

async def run_bot():
    print("--- [START] Avvio estrazione PROGRAMMI GARE (In corso: 30 giorni fa -> Oggi) ---")
    async with async_playwright() as p:
        # Lasciato a False per vedere a schermo che compaiono i tornei giusti
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Processo categoria: {cat_id}")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            await page.goto(BASE_URL, timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            # --- 1. IMPOSTAZIONE DATE DI RICERCA (30 giorni fa -> Oggi) ---
            oggi = datetime.now()
            data_inizio = (oggi - timedelta(days=30)).strftime("%d/%m/%Y")
            data_fine = oggi.strftime("%d/%m/%Y")
            
            print(f"-> Impostazione date nei campi: da {data_inizio} a {data_fine}")
            
            # Compilazione sicura dei campi data con eventi JS
            await page.locator("#dpk_start_date").evaluate(f"(el) => {{ el.value = '{data_inizio}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); el.dispatchEvent(new Event('change', {{ bubbles: true }})); el.dispatchEvent(new Event('blur', {{ bubbles: true }})); }}")
            await page.locator("#dpk_end_date").evaluate(f"(el) => {{ el.value = '{data_fine}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); el.dispatchEvent(new Event('change', {{ bubbles: true }})); el.dispatchEvent(new Event('blur', {{ bubbles: true }})); }}")
            await asyncio.sleep(2)
            
            # --- 2. APPLICAZIONE DEI FILTRI ---
            # Stato: In corso
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name=re.compile("in corso", re.IGNORECASE)).click()
            await asyncio.sleep(2)
            
            # Regione: Lazio
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(2)
            
            # Provincia: Roma
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(2)
            
            # --- 3. CLIC SUL PULSANTE "CERCA" ---
            print("-> Clic sul pulsante Cerca del portale...")
            try:
                btn_cerca = page.locator("button.btn.btn-primary:has-text('Cerca'), button:has-text('Cerca')")
                if await btn_cerca.count() > 0:
                    await btn_cerca.first.click()
                    await asyncio.sleep(5) # Attende il caricamento dei risultati filtrati
            except Exception as e:
                print(f"   (Errore click cerca: {e})")

            # --- 4. SELEZIONE CATEGORIA ---
            print(f"-> Attendendo categoria {cat_id}...")
            cat_selector = f'a[data-id="{cat_id}"]'
            await page.wait_for_selector(cat_selector, timeout=30000)
            await page.locator(cat_selector).first.click()
            await asyncio.sleep(6)
            
            # --- 5. ESPANSIONE LISTA ---
            print("-> Espansione lista tornei...")
            while True:
                btn_load_more = page.locator("#btn-loadMore")
                if await btn_load_more.is_visible():
                    await btn_load_more.click()
                    await asyncio.sleep(6)
                else:
                    break
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            print(f"-> Trovati {len(links)} tornei. Inizio analisi...")
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                await page.goto(full_url, timeout=60000)
                
                try:
                    nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                except:
                    nome_torneo = "Torneo senza nome"
                
                print(f"   [Analizzo]: {nome_torneo.strip()}")
                
                dropdown_selector = "#select-ordergame"
                download_btn = page.locator("#btnOrderGameDownload")
                
                if await page.locator(dropdown_selector).is_visible():
                    for i in range(0, 2):  # Oggi e Domani per i PDF
                        data_target = (oggi + timedelta(days=i)).strftime("%d/%m/%Y")
                        
                        if await page.locator(f"{dropdown_selector} option:has-text('{data_target}')").count() > 0:
                            await page.select_option(dropdown_selector, label=data_target)
                            await asyncio.sleep(5)
                            
                            if await download_btn.is_visible():
                                async with page.expect_download() as dl_info: 
                                    await download_btn.click()
                                download = await dl_info.value
                                await download.save_as("temp.pdf")
                                matches = get_pdf_info("temp.pdf")
                                json_data["tornei"].append({
                                    "url": full_url, 
                                    "nomeTorneo": nome_torneo.strip(), 
                                    "data": data_target, 
                                    "partite": [format_line_for_swift(m, data_target) for m in matches] if matches else ["Nessuna partita trovata"]
                                })
                        else:
                            json_data["tornei"].append({
                                "url": full_url, 
                                "nomeTorneo": nome_torneo.strip(), 
                                "data": data_target, 
                                "partite": ["Nessuna partita trovata"]
                            })
                
                elif await download_btn.is_visible():
                    async with page.expect_download() as dl_info: 
                        await download_btn.click()
                    download = await dl_info.value
                    await download.save_as("temp.pdf")
                    matches = get_pdf_info("temp.pdf")
                    data_oggi = datetime.now().strftime("%d/%m/%Y")
                    json_data["tornei"].append({
                        "url": full_url, 
                        "nomeTorneo": nome_torneo.strip(), 
                        "data": data_oggi, 
                        "partite": [format_line_for_swift(m, "Oggi") for m in matches] if matches else ["Nessuna partita trovata"]
                    })
                else:
                    print(f"      ! Tabellone non disponibile.")
                    json_data["tornei"].append({
                        "url": full_url, 
                        "nomeTorneo": nome_torneo.strip(), 
                        "data": datetime.now().strftime("%d/%m/%Y"), 
                        "partite": ["Tabellone non disponibile"]
                    })
            
            with open(filename, "w", encoding="utf-8") as f: 
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            await page.close()
        
        await browser.close()
    print("--- [END] Processo completato ---")

if __name__ == "__main__": 
    asyncio.run(run_bot())
