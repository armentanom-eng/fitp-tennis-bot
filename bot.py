import asyncio
import os
import pdfplumber
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

URL_BASE = "https://www.fitp.it"
URL_RICERCA = f"{URL_BASE}/Tornei/Ricerca-tornei"

def salva_risultati(file_output, nome_torneo, data_str, partite):
    """Aggiunge i dati al file (append mode)."""
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
                text = page.extract_text()
                if not text: continue
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if "Inizio ore:" in line:
                        ora = line.replace("Inizio ore:", "").strip()
                        g1 = lines[i+1].strip() if i+1 < len(lines) else "N/A"
                        g2 = lines[i+3].strip() if i+3 < len(lines) else "N/A"
                        partite.append(f"{g1}; {g2}; {ora}")
    except Exception as e:
        print(f"    [!] Errore estrazione PDF: {e}")
    return partite

async def get_tournament_links(page, categoria_id):
    """Naviga e trova i link, gestendo la strict mode con .first"""
    print(f"[*] Navigazione su pagina ricerca...")
    await page.goto(URL_RICERCA, wait_until="networkidle")
    
    await page.select_option("#select_status", label="In corso")
    await page.click('button[data-id="id_regioneSearch"]')
    await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
    
    print(f"[*] Selezione categoria ID: {categoria_id}")
    
    # AGGIUNTA .first: Risolve la 'strict mode violation' prendendo solo il primo elemento
    tab = page.locator(f'a[data-id="{categoria_id}"]').first
    
    await tab.wait_for(state="visible", timeout=15000)
    await tab.click()
    await page.wait_for_timeout(3000)

    print(f"[*] Caricamento tornei...")
    while True:
        btn = page.locator("#btn-loadMore")
        if await btn.is_visible():
            await btn.click()
            await asyncio.sleep(2)
        else:
            break
        
    elements = await page.locator("a[href*='Dettaglio-Competizione']").all()
    links = list(set([await el.get_attribute("href") for el in elements]))
    
    if not links:
        print(f"  [!] ATTENZIONE: Nessun torneo trovato per {categoria_id}")
    else:
        print(f"[*] Trovati {len(links)} tornei.")
    return links

async def process_tournament(page, url, file_output):
    """Entra nel torneo, seleziona date e scarica PDF."""
    try:
        await page.goto(f"{URL_BASE}{url}", wait_until="domcontentloaded")
        nome_torneo = await page.locator("h1").first.inner_text()
        print(f"  -> Elaborazione: {nome_torneo}")
        
        oggi = datetime.now().strftime("%d/%m/%Y")
        domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
        
        for data_target in [oggi, domani]:
            try:
                await page.wait_for_selector("select[name='data_programma']")
                await page.select_option("select[name='data_programma']", label=data_target)
                
                async with page.expect_download(timeout=10000) as download_info:
                    await page.click("#btnOrderGameDownload")
                
                download = await download_info.value
                path = f"temp_{data_target.replace('/', '')}.pdf"
                await download.save_as(path)
                
                partite = estrai_da_pdf(path)
                if partite:
                    salva_risultati(file_output, nome_torneo, data_target, partite)
                    print(f"     [OK] {data_target}: {len(partite)} match estratti.")
                
                if os.path.exists(path): os.remove(path)
            except:
                continue 
    except Exception as e:
        print(f"  [!] Errore su {url}: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        # Mappa categorie
        config = [("t_giovanili", "Giovanili_Partite.txt"), ("t_affiliati", "Open_Partite.txt")]
        
        for cat_id, file_out in config:
            print(f"\n--- Inizio sessione: {file_out} ---")
            # Reset file
            with open(file_out, "w", encoding="utf-8") as f:
                f.write(f"Report del {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            
            p_nav = await context.new_page()
            try:
                links = await get_tournament_links(p_nav, cat_id)
                await p_nav.close()
                
                for link in links:
                    p_proc = await context.new_page()
                    await process_tournament(p_proc, link, file_out)
                    await p_proc.close()
            except Exception as e:
                print(f"Errore critico cat {cat_id}: {e}")
        
        print(f"\n--- Processo completato ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())