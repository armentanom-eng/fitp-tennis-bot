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
    """Salva i dati nel formato richiesto."""
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"\n{tournament_name}\n")
        for match in matches:
            f.write(f"{date_str}; {match}\n")

def parse_pdf(pdf_path):
    """Estrae i dati dai PDF."""
    results = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if "Inizio ore:" in line:
                        ora = line.replace("Inizio ore:", "").strip()
                        # Logica di estrazione basata sulla struttura PDF
                        p1 = lines[i+1].strip() if i+1 < len(lines) else "N/A"
                        p2 = lines[i+3].strip() if i+3 < len(lines) else "N/A"
                        results.append(f"{p1}; {p2}; {ora}")
    except Exception as e:
        print(f"Errore PDF: {e}")
    return results

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            # Reset file ogni giorno
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Report del {datetime.now().strftime('%d/%m/%Y')}\n")
            
            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Filtri: Lazio, In corso, Tennis
            await page.select_option("#select_status", label="In corso")
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            
            # Selezione Categoria
            await page.locator(f'a[data-id="{cat_id}"]').click()
            await page.wait_for_timeout(2000)
            
            # Caricamento dinamico "Altri Dati"
            while True:
                load_more = page.locator("#btn-loadMore")
                if await load_more.is_visible():
                    await load_more.click()
                    await asyncio.sleep(2)
                else:
                    break
            
            # Estrazione Link Tornei
            links = await page.locator("a[href*='Dettaglio-Competizione']").all_attribute_values("href")
            links = list(set(links)) # Rimuovi duplicati
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                await page.goto(full_url, wait_until="domcontentloaded")
                
                # Selezione date
                dates = [datetime.now(), datetime.now() + timedelta(days=1)]
                tournament_name = await page.locator("h1").first.inner_text()
                
                for d in dates:
                    date_str = d.strftime("%d/%m/%Y")
                    try:
                        await page.select_option("#select-ordergame", label=date_str)
                        await page.dispatch_event("#select-ordergame", "change")
                        await asyncio.sleep(2)
                        
                        async with page.expect_download() as dl_info:
                            await page.click("#btnOrderGameDownload")
                        
                        dl = await dl_info.value
                        await dl.save_as("temp.pdf")
                        matches = parse_pdf("temp.pdf")
                        if matches:
                            save_to_file(filename, tournament_name, date_str, matches)
                        os.remove("temp.pdf")
                    except:
                        continue
            await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
