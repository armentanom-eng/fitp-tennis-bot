import asyncio
import os
import pdfplumber
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

def parse_pdf(file_path, nome_torneo, data_str, file_output):
    """Estrae dati dal PDF e li AGGIUNGE al file (modalità 'a')."""
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    
    # 'a' sta per append: aggiunge al fondo senza sovrascrivere
    with open(file_output, "a", encoding="utf-8") as f:
        f.write(f"\n>> {nome_torneo}\n")
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if "Inizio ore:" in line:
                ora = line.replace("Inizio ore:", "").strip()
                # Logica per estrarre i nomi
                g1 = lines[i+1].strip() if i+1 < len(lines) else ""
                g2 = lines[i+3].strip() if i+3 < len(lines) else ""
                f.write(f"{data_str}; {g1}; {g2}; {ora}\n")

async def get_tournament_links(page, categoria_tab_name):
    await page.goto(URL, wait_until="networkidle")
    
    # Filtri
    await page.select_option("#select_status", label="In corso")
    await page.click('button[data-id="id_regioneSearch"]')
    await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
    
    # Categoria (Tab)
    await page.get_by_role("link", name=categoria_tab_name).click()
    await page.wait_for_timeout(2000)

    # Paginazione
    while await page.locator("#btn-loadMore").is_visible():
        await page.click("#btn-loadMore")
        await asyncio.sleep(1)
        
    elements = await page.locator("a[href*='Dettaglio-Competizione']").all()
    return list(set([await el.get_attribute("href") for el in elements]))

async def process_tournament(page, url, file_output):
    await page.goto(f"https://www.fitp.it{url}")
    
    oggi = datetime.now().strftime("%d/%m/%Y")
    domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    for data_target in [oggi, domani]:
        try:
            # Seleziona data nel dropdown
            await page.select_option("select[name='data_programma']", label=data_target)
            
            async with page.expect_download() as download_info:
                await page.click("#btnOrderGameDownload")
            
            download = await download_info.value
            path = f"temp_{data_target.replace('/', '')}.pdf"
            await download.save_as(path)
            
            # Estrazione
            nome_torneo = await page.locator("h1").first.inner_text()
            parse_pdf(path, nome_torneo, data_target, file_output)
            
            if os.path.exists(path): os.remove(path)
        except Exception:
            # Se la data non esiste o il tasto non c'è, saltiamo
            continue

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        # Mappa categorie -> file
        categorie = [("TORNEI GIOVANILI", "Giovanili_Partite.txt"), ("TORNEI OPEN", "Open_Partite.txt")]
        
        for tab_name, file_out in categorie:
            # Rimosso il comando os.remove: ora il file non viene più cancellato!
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
