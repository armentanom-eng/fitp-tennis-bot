import asyncio
import pdfplumber
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

# Nomi file aggiornati come richiesto
CATEGORIES = {
    "t_giovanili": "Iscrizioni_Aperte_Giovanili.json", 
    "t_affiliati": "Iscrizioni_Aperte_Open.json"
}

async def run_bot():
    print("--- [START] Avvio estrazione ISCRIZIONI APERTE ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Processo categoria: {cat_id}")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            await page.goto(BASE_URL, timeout=60000)
            
            # --- FILTRO STATO FORZATO ---
            await page.click('button[data-id="select_status"]')
            await page.wait_for_selector('div.dropdown-menu.show')
            await page.locator('span.text:has-text("Iscrizioni aperte")').click()
            await asyncio.sleep(3)
            
            # --- FILTRI GEOGRAFICI ---
            await page.click('button[data-id="id_regioneSearch"]')
            await page.locator('span.text:has-text("Lazio")').click()
            await asyncio.sleep(2)
            
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.locator('span.text:has-text("Roma")').click()
            await asyncio.sleep(2)
            
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)
            
            # Selezione categoria (Giovanili/Open)
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(5)
            
            # Espansione lista
            print("-> Espansione lista tornei...")
            while True:
                btn_load_more = page.locator("#btn-loadMore")
                if await btn_load_more.is_visible():
                    await btn_load_more.click()
                    await asyncio.sleep(4)
                else:
                    break
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators if await loc.get_attribute("href")]))
            
            print(f"-> Trovati {len(links)} tornei.")
            
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                await page.goto(full_url, timeout=60000)
                
                try:
                    nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                except:
                    nome_torneo = "Torneo senza nome"
                
                download_btn = page.locator("#btnOrderGameDownload")
                if await download_btn.is_visible():
                    async with page.expect_download() as dl_info: 
                        await download_btn.click()
                    download = await dl_info.value
                    await download.save_as("temp.pdf")
                    json_data["tornei"].append({"url": full_url, "nomeTorneo": nome_torneo.strip(), "status": "PDF scaricato"})
                else:
                    json_data["tornei"].append({"url": full_url, "nomeTorneo": nome_torneo.strip(), "status": "Nessun PDF"})
            
            with open(filename, "w", encoding="utf-8") as f: 
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            await page.close()
            
        await browser.close()
    print("--- [END] Processo completato correttamente ---")

if __name__ == "__main__": 
    asyncio.run(run_bot())
