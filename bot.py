import asyncio
import os
import pdfplumber
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

URL_BASE = "https://www.fitp.it"
URL_RICERCA = f"{URL_BASE}/Tornei/Ricerca-tornei"

def salva_risultati(file_output, nome_torneo, data_str, partite):
    with open(file_output, "a", encoding="utf-8") as f:
        f.write(f"\n>> {nome_torneo}\n")
        for p in partite:
            f.write(f"{data_str}; {p}\n")

def estrai_da_pdf(file_path):
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
        print(f"    [!] Errore estrazione PDF: {e}", flush=True)
    return partite

async def get_tournament_links(page, categoria_id):
    print(f"[*] Navigazione su pagina ricerca...", flush=True)
    await page.goto(URL_RICERCA, wait_until="networkidle")
    
    await page.select_option("#select_status", label="In corso")
    await page.click('button[data-id="id_regioneSearch"]')
    await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
    
    tab = page.locator(f'a[data-id="{categoria_id}"]').first
    await tab.click()
    await page.wait_for_timeout(3000)

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
    try:
        full_url = f"{URL_BASE}{url}" if url.startswith('/') else url
        await page.goto(full_url, wait_until="domcontentloaded")
        
        nome_torneo = await page.locator("h1").first.inner_text()
        print(f"  -> Elaborazione: {nome_torneo}", flush=True)
        
        oggi = datetime.now().strftime("%d/%m/%Y")
        domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
        
        # Il selettore dell'input che apre il menu delle date
        # (Cerchiamo l'input che si trova vicino alla scritta 'Orario di Gioco')
        input_data = page.locator("xpath=//label[contains(text(), 'Orario di Gioco')]/following::input[1]")
        
        for data_target in [oggi, domani]:
            try:
                # 1. Apriamo il menu cliccando sull'input
                await input_data.click()
                
                # 2. Clicchiamo sulla data specifica (usando il testo esatto che appare nella lista)
                # Diamo tempo al menu di apparire
                data_option = page.get_by_text(data_target, exact=True)
                await data_option.wait_for(state="visible", timeout=5000)
                await data_option.click()
                
                # 3. Clicchiamo su scarica
                # Usiamo locator per trovare il bottone 'Scarica' vicino all'input
                btn_scarica = page.locator("xpath=//label[contains(text(), 'Orario di Gioco')]/following::button[contains(text(), 'Scarica')][1]")
                
                async with page.expect_download(timeout=10000) as download_info:
                    await btn_scarica.click()
                
                download = await download_info.value
                path = f"temp_{data_target.replace('/', '')}.pdf"
                await download.save_as(path)
                
                partite = estrai_da_pdf(path)
                if partite:
                    salva_risultati(file_output, nome_torneo, data_target, partite)
                    print(f"     [OK] {data_target}: {len(partite)} match estratti.", flush=True)
                
                if os.path.exists(path): os.remove(path)
                
            except Exception as e:
                print(f"     [-] Data {data_target} non disponibile o menu non trovato.", flush=True)
                continue 
    except Exception as e:
        print(f"  [!] Errore su {url}: {e}", flush=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        config = [("t_giovanili", "Giovanili_Partite.txt"), ("t_affiliati", "Open_Partite.txt")]
        
        for cat_id, file_out in config:
            print(f"\n--- Sessione: {file_out} ---", flush=True)
            with open(file_out, "w", encoding="utf-8") as f:
                f.write(f"Report del {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            
            p_nav = await context.new_page()
            links = await get_tournament_links(p_nav, cat_id)
            await p_nav.close()
            
            for link in links:
                p_proc = await context.new_page()
                await process_tournament(p_proc, link, file_out)
                await p_proc.close()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
