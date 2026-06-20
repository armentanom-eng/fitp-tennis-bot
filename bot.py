import asyncio
import os
import pdfplumber
from playwright.async_api import async_playwright
from datetime import datetime, timedelta

CONCURRENT_PAGES = 5 

def estrai_dati_da_pdf(percorso_pdf, data_target):
    partite_trovate = []
    nome_circolo = "Circolo Non Trovato"
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            if not pdf.pages: return None, []
            testo = pdf.pages[0].extract_text()
            if not testo: return None, []
            linee = testo.split('\n')
            nome_circolo = linee[0].strip()
            for i in range(len(linee)):
                if "Inizio ore:" in linee[i]:
                    orario = linee[i].replace("Inizio ore:", "").strip()
                    try:
                        g1 = linee[i+2].strip()
                        g2 = linee[i+4].strip()
                        if "vs" not in g1.lower() and len(g1) > 4:
                             partite_trovate.append(f"{g1}; {g2}; {orario}")
                    except: continue
    except: pass
    return nome_circolo, partite_trovate

async def get_tournament_urls(page, categoria_id):
    print(f"[{categoria_id}] Raccolta URL per il Lazio in corso...")
    # Navigazione iniziale
    await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
    
    # 1. Filtro Stato e Categoria
    await page.select_option("#select_status", label="In corso")
    await page.click(f'a[data-id="{categoria_id}"]')
    
    # 2. FILTRO REGIONE (Usiamo l'ID trovato nello screenshot)
    try:
        await page.select_option("#id_regioneSearch", label="Lazio")
        # Attesa necessaria perché il sito ricarica i risultati via AJAX
        await asyncio.sleep(3) 
    except Exception as e:
        print(f"Errore filtro regione: {e}")
    
    # Caricamento infinito
    while True:
        btn = page.locator("#btn-loadMore")
        if await btn.is_visible():
            await btn.click()
            await asyncio.sleep(1.5)
        else:
            break
            
    elements = await page.locator("a[href*='Dettaglio-Competizione']").all()
    urls = []
    for el in elements:
        url = await el.get_attribute("href")
        if url and url not in urls: urls.append(url)
    return urls

async def process_tournament(context, url, sem, nome_file):
    async with sem:
        full_url = "https://www.fitp.it" + url
        page = await context.new_page()
        try:
            await page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
            oggi = datetime.now().strftime("%d/%m/%Y")
            domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
            
            for data in [oggi, domani]:
                try:
                    if await page.locator("select").count() > 0:
                        await page.select_option("select", label=data)
                        await asyncio.sleep(1) 
                        
                        btn = page.locator("text=Scarica")
                        if await btn.is_visible():
                            async with page.expect_download(timeout=15000) as download_info:
                                await btn.click()
                            download = await download_info.value
                            temp_file = f"temp_{data.replace('/', '-')}.pdf"
                            await download.save_as(temp_file)
                            
                            nome, partite = estrai_dati_da_pdf(temp_file, data)
                            if nome and partite:
                                with open(nome_file, "a", encoding="utf-8") as f:
                                    f.write(f"\n>> {nome} (Data: {data})\n" + "\n".join(partite) + "\n")
                            if os.path.exists(temp_file): os.remove(temp_file)
                except: continue
        except Exception as e:
            print(f"Errore su {url}: {e}")
        finally:
            await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        sem = asyncio.Semaphore(CONCURRENT_PAGES)
        
        categorie = [("t_giovanili", "Giovanili_Partite.txt"), ("t_affiliati", "Open_Partite.txt")]
        
        for cat_id, file_name in categorie:
            p_scout = await context.new_page()
            # Assicuriamo che 'urls' sia sempre definito come lista vuota se non trova nulla
            urls = await get_tournament_urls(p_scout, cat_id) or []
            await p_scout.close()
            
            print(f"[{cat_id}] Trovati {len(urls)} tornei. Avvio elaborazione...")
            if urls:
                tasks = [process_tournament(context, url, sem, file_name) for url in urls]
                await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
