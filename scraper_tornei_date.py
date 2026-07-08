import asyncio
import os
import pdfplumber
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    oggi_str = datetime.now().strftime("%d/%m/%Y")
    domani_str = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    # Inizializzazione dati
    dati_giovanili = {"tornei": []}
    dati_open = {"tornei": []}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        # Filtri
        await page.click('button[data-id="select_status"]')
        await page.locator('span:text-is("In programma")').last.click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # Espansione lista
        while True:
            btn = page.locator("button#btn-loadMore")
            if await btn.is_visible(): 
                await btn.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
            else: break
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        print(f"Trovati {len(urls)} tornei. Inizio analisi...")
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            print(f"-> Analizzo: {full_url.split('/')[-1]}", flush=True)
            
            try:
                await page.goto(full_url, wait_until="networkidle")
                
                # Identifica se è giovanile per dividere i dati
                titolo = await page.locator("h1.cc-title-main").first.text_content()
                is_giovanile = any(kw in (titolo or "").lower() for kw in ["under", "u10", "u12", "u14", "u16"])
                target_list = dati_giovanili if is_giovanile else dati_open
                
                dropdown = page.locator("#select-ordergame")
                if not await dropdown.is_visible():
                    print("   [!] Nessun ordine di gioco disponibile. Salto.")
                    continue
                
                for data_target in [oggi_str, domani_str]:
                    if await page.locator(f"#select-ordergame option:has-text('{data_target}')").count() > 0:
                        print(f"   [+] Data {data_target} trovata. Preparo download.")
                        await page.select_option("#select-ordergame", label=data_target)
                        await asyncio.sleep(2)
                        
                        btn_download = page.locator("#btnOrderGameDownload")
                        if await btn_download.is_visible():
                            async with page.expect_download(timeout=15000) as dl_info:
                                await btn_download.click()
                            
                            download = await dl_info.value
                            temp_path = "temp_file.pdf"
                            await download.save_as(temp_path)
                            
                            # Logica di salvataggio nel file corretto
                            target_list["tornei"].append({"url": full_url, "data": data_target, "info": "PDF scaricato"})
                            
                            print(f"   [v] PDF scaricato correttamente.")
                            if os.path.exists(temp_path): os.remove(temp_path)
                        else:
                            print("   [-] Tasto download non trovato per questa data.")
            
            except Exception as e:
                print(f"   [x] Errore su {url}: {e}")
                continue
        
        # Scrittura finale nei file richiesti
        with open("Tornei_Date_Giovanili_In_Programma_PDF.json", "w", encoding="utf-8") as f:
            json.dump(dati_giovanili, f, ensure_ascii=False, indent=4)
        with open("Tornei_Date_Open_In_Programa_Pdf.json", "w", encoding="utf-8") as f:
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        print("--- Bot completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
