import asyncio
import os
import pdfplumber
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {
    "t_giovanili": "Giovanili_Partite.txt",
    "t_affiliati": "Open_Partite.txt"
}

def save_to_file(filename, tournament_name, date_str, matches):
    """Salva nel formato: Data; Giocatore1; Giocatore2; Orario"""
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"\n{tournament_name}\n")
        for match in matches:
            f.write(f"{date_str}; {match}\n")

def parse_pdf(pdf_path):
    """Estrae dati: G1; G2; Ora"""
    results = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                for i, line in enumerate(lines):
                    if "Inizio ore:" in line:
                        ora = line.replace("Inizio ore:", "").strip()
                        g1 = lines[i+1] if i+1 < len(lines) else "N/A"
                        g2 = lines[i+3] if i+3 < len(lines) else "N/A"
                        results.append(f"{g1}; {g2}; {ora}")
    except Exception as e:
        print(f"    [!] Errore PDF: {e}", flush=True)
    return results

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n--- Inizio sessione: {filename} ---", flush=True)
            # Resetta il file ogni volta
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Report del {datetime.now().strftime('%d/%m/%Y')}\n")
            
            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Filtri base
            await page.select_option("#select_status", label="In corso")
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            
            # Selezione Categoria (Fix Strict Mode con .first)
            print(f"[*] Selezione categoria: {cat_id}", flush=True)
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await page.wait_for_timeout(3000)
            
            # Caricamento dinamico "Altri Dati"
            while True:
                load_more = page.locator("#btn-loadMore")
                if await load_more.is_visible():
                    print("[*] Caricamento ulteriori risultati...", flush=True)
                    await load_more.click()
                    await asyncio.sleep(3)
                else:
                    break
            
            # Estrazione Link
            links = await page.locator("a[href*='Dettaglio-Competizione']").all_attribute_values("href")
            links = list(set(links))
            print(f"[*] Trovati {len(links)} tornei.", flush=True)
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                await page.goto(full_url, wait_until="domcontentloaded")
                tournament_name = await page.locator("h1").first.inner_text()
                print(f"  -> {tournament_name}", flush=True)
                
                # Date: oggi e domani
                for i in range(2):
                    date_target = datetime.now() + timedelta(days=i)
                    date_str = date_target.strftime("%d/%m/%Y")
                    
                    try:
                        # Selezione data
                        if await page.locator("#select-ordergame").count() > 0:
                            await page.select_option("#select-ordergame", label=date_str)
                            await page.dispatch_event("#select-ordergame", "change")
                            await asyncio.sleep(2)
                            
                            # Download
                            async with page.expect_download(timeout=10000) as dl_info:
                                await page.click("#btnOrderGameDownload")
                            
                            dl = await dl_info.value
                            await dl.save_as("temp.pdf")
                            matches = parse_pdf("temp.pdf")
                            if matches:
                                save_to_file(filename, tournament_name, date_str, matches)
                                print(f"     [OK] {date_str}: {len(matches)} match.", flush=True)
                            if os.path.exists("temp.pdf"): os.remove("temp.pdf")
                    except:
                        print(f"     [-] Nessuna gara per {date_str}", flush=True)
