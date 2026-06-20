import asyncio
import os
import pdfplumber
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

def salva_nel_file(file_output, nome_torneo, data_str, partite):
    """Aggiunge le partite al file esistente."""
    with open(file_output, "a", encoding="utf-8") as f:
        f.write(f"\n>> {nome_torneo}\n")
        for p in partite:
            f.write(f"{data_str}; {p}\n")

def estrai_da_pdf(file_path):
    """Legge il PDF ed estrae i dati."""
    partite = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                lines = page.extract_text().split('\n')
                for i, line in enumerate(lines):
                    if "Inizio ore:" in line:
                        ora = line.replace("Inizio ore:", "").strip()
                        g1 = lines[i+1].strip() if i+1 < len(lines) else ""
                        g2 = lines[i+3].strip() if i+3 < len(lines) else ""
                        partite.append(f"{g1}; {g2}; {ora}")
    except: pass
    return partite

async def get_tournament_links(page, categoria_tab_name):
    await page.goto(URL, wait_until="networkidle")
    await page.select_option("#select_status", label="In corso")
    await page.click('button[data-id="id_regioneSearch"]')
    await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
    
    await page.get_by_role("link", name=categoria_tab_name).click()
    await page.wait_for_timeout(2000)

    # Paginazione: continua a cliccare finché il tasto c'è
    while True:
        btn = page.locator("#btn-loadMore")
        if await btn.is_visible():
            await btn.click()
            await asyncio.sleep(2)
        else:
            break
        
    elements = await page.locator("a[href*='Dettaglio-Competizione']").all()
    return list(set([await el.get_attribute("href") for el in elements]))

async def process_tournament(page, url, file_output):
    await page.goto(f"https://www.fitp.it{url}")
    nome_torneo = await page.locator("h1").first.inner_text()
    
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    for data_target in [oggi, domani]:
        try:
            await page.select_option("select[name='data_programma']", label=data_target)
            async with page.expect_download() as download_info:
                await page.click("#btnOrderGameDownload")
            
            download = await download_info.value
            path = f"temp_{data_target.replace('/', '')}.pdf"
            await download.save_as(path)
            
            partite = estrai_da_pdf(path)
            if partite:
                salva_nel_file(file_output, nome_torneo, data_target, partite)
            
            if os.path.exists(path): os.remove(path)
        except Exception:
            continue

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        categorie = [("TORNEI GIOVANILI", "Giovanili_Partite.txt"), ("TORNEI OPEN", "Open_Partite.txt")]
        
        for tab_name, file_out in categorie:
            # RESET DEL FILE: apre in 'w' e chiude subito, svuotando il contenuto
            with open(file_out, "w", encoding="utf-8") as f:
                f.write(f"Report del {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            
            p_nav = await context.new_page()
            links = await get_tournament_links(p_nav, tab_name)
            await p_nav.close()
            
            for link in links:
                p_proc = await context.new_page()
                await process_tournament(p_proc, link, file_out)
                await p_proc.close()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
