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
            print(f"\n--- Inizio sessione: {filename} ---", flush=True)
            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Filtri
            await page.select_option("#select_status", label="In corso")
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            
            # Categoria
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await page.wait_for_timeout(3000)
            
            # Carica tutti i risultati
            while True:
                btn = page.locator("#btn-loadMore")
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(2)
                else:
                    break
            
            # Recupera URL tornei
            links = await page.locator("a[href*='Dettaglio-Competizione']").all_attribute_values("href")
            links = list(set(links))
            print(f"[*] Trovati {len(links)} tornei.", flush=True)
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                await page.goto(full_url, wait_until="networkidle")
                nome = await page.locator("h1").first.inner_text()
                print(f"  -> Elaborando: {nome}", flush=True)
                
                # ORA: Aspettiamo il menù a tendina con pazienza
                try:
                    # Aspetta fino a 15 secondi che il menù sia visibile
                    await page.wait_for_selector("#select-ordergame", timeout=15000)
                    
                    # Date: Oggi e Domani
                    for i in range(2):
                        data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                        
                        try:
                            # Tentiamo di selezionare la data
                            # usiamo 'label' per essere precisi
                            await page.select_option("#select-ordergame", label=data_target)
                            await page.wait_for_timeout(2000) # Tempo per aggiornare la pagina
                            
                            # Clicchiamo il tasto download
                            async with page.expect_download(timeout=10000) as dl_info:
                                await page.click("#btnOrderGameDownload")
                            
                            dl = await dl_info.value
                            path = "temp.pdf"
                            await dl.save_as(path)
                            
                            # Lettura dati
                            with pdfplumber.open(path) as pdf:
                                save_data(filename, f">> {nome} ({data_target})")
                                for page_pdf in pdf.pages:
                                    text = page_pdf.extract_text()
                                    if text:
                                        for line in text.split('\n'):
                                            if "Inizio ore:" in line:
                                                save_data(filename, f"{data_target}; {line.strip()}")
                            if os.path.exists(path): os.remove(path)
                            print(f"     [OK] Scaricato PDF per {data_target}", flush=True)
                        except Exception:
                            print(f"     [-] Nessuna gara per {data_target}", flush=True)
                            
                except Exception as e:
                    print(f"     [!] Errore critico menù date: {e}", flush=True)
            
            await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
