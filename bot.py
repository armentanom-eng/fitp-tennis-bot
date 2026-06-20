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

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"--- Inizio sessione: {filename} ---", flush=True)
            
            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Filtri
            await page.select_option("#select_status", label="In corso")
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            
            # Categoria
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await page.wait_for_timeout(3000)
            
            # Carica tutto
            while True:
                btn = page.locator("#btn-loadMore")
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(2)
                else:
                    break
            
            # Recupera URL tornei
            elements = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = []
            for el in elements:
                links.append(await el.get_attribute("href"))
            links = list(set(links))
            
            print(f"[*] Trovati {len(links)} tornei.", flush=True)
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                await page.goto(full_url, wait_until="domcontentloaded")
                nome = await page.locator("h1").first.inner_text()
                print(f"  -> {nome}", flush=True)
                
                # Date
                for i in range(2):
                    data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                    
                    # Verifica menu
                    dropdown = page.locator("#select-ordergame")
                    if await dropdown.count() > 0:
                        try:
                            await dropdown.select_option(label=data_target)
                            await page.wait_for_timeout(2000)
                            
                            # Download
                            async with page.expect_download(timeout=10000) as dl_info:
                                await page.click("#btnOrderGameDownload")
                            
                            dl = await dl_info.value
                            path = "temp.pdf"
                            await dl.save_as(path)
                            
                            # Lettura
                            with pdfplumber.open(path) as pdf:
                                save_data(filename, f">> {nome} ({data_target})")
                                for page_pdf in pdf.pages:
                                    text = page_pdf.extract_text()
                                    if text:
                                        for line in text.split('\n'):
                                            if "Inizio ore:" in line:
                                                save_data(filename, f"{data_target}; {line.strip()}")
                            if os.path.exists(path): os.remove(path)
                            print(f"     [OK] {data_target}", flush=True)
                        except Exception as e:
                            print(f"     [!] Errore su {data_target}: {e}", flush=True)
                    else:
                        print(f"     [-] Menu date non trovato", flush=True)
            await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
