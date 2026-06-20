import asyncio
import os
import pdfplumber
from playwright.async_api import async_playwright

CONCURRENT_PAGES = 5 
URL_BASE = "https://www.fitp.it"

def estrai_dati_da_pdf(percorso_pdf):
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            if not pdf.pages: return None, []
            testo = pdf.pages[0].extract_text()
            if not testo: return None, []
            linee = testo.split('\n')
            nome_circolo = linee[0].strip()
            partite_trovate = []
            for i in range(len(linee)):
                if "Inizio ore:" in linee[i]:
                    orario = linee[i].replace("Inizio ore:", "").strip()
                    try:
                        g1 = linee[i+2].strip()
                        g2 = linee[i+4].strip()
                        if "vs" not in g1.lower() and len(g1) > 4:
                             partite_trovate.append(f"{g1}; {g2}; {orario}")
                    except: continue
            return nome_circolo, partite_trovate
    except: return "Errore", []

async def get_tournament_urls(page, categoria_id):
    await page.goto(f"{URL_BASE}/Tornei/Ricerca-tornei", wait_until="networkidle")
    await page.select_option("#select_status", label="In corso")
    await page.click(f'a[data-id="{categoria_id}"]')
    
    # Filtro Regione Lazio - FIXED con .first
    await page.click('button[data-id="id_regioneSearch"]')
    await page.locator('span.text:has-text("Lazio")').first.click() 
    await page.wait_for_load_state("networkidle")
    
    # Caricamento completo
    while await page.locator("#btn-loadMore").is_visible():
        await page.click("#btn-loadMore")
        await asyncio.sleep(1)
            
    elements = await page.locator("a[href*='Dettaglio-Competizione']").all()
    return list(set([await el.get_attribute("href") for el in elements]))

async def process_tournament(context, url, sem, nome_file, index):
    async with sem:
        page = await context.new_page()
        try:
            await page.goto(URL_BASE + url, wait_until="domcontentloaded", timeout=60000)
            btn = page.locator("text=Scarica")
            if await btn.is_visible():
                async with page.expect_download(timeout=10000) as download_info:
                    await btn.click()
                download = await download_info.value
                path = f"temp_{index}.pdf"
                await download.save_as(path)
                
                nome, partite = estrai_dati_da_pdf(path)
                if nome and partite:
                    with open(nome_file, "a", encoding="utf-8") as f:
                        f.write(f"\n>> {nome}\n" + "\n".join(partite) + "\n")
                if os.path.exists(path): os.remove(path)
        except Exception as e:
            print(f"Errore su {url}: {e}")
        finally:
            await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # FONDAMENTALE
        context = await browser.new_context(accept_downloads=True)
        sem = asyncio.Semaphore(CONCURRENT_PAGES)
        
        categorie = [("t_giovanili", "Giovanili.txt"), ("t_affiliati", "Open.txt")]
        
        for cat_id, file_name in categorie:
            if os.path.exists(file_name): os.remove(file_name)
            p_scout = await context.new_page()
            urls = await get_tournament_urls(p_scout, cat_id)
            await p_scout.close()
            
            if urls:
                tasks = [process_tournament(context, url, sem, file_name, i) for i, url in enumerate(urls)]
                await asyncio.gather(*tasks)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
