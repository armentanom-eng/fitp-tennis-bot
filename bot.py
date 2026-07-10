import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

CATEGORIES = {
    "t_giovanili": "Iscrizioni_Aperte_Giovanili.json", 
    "t_affiliati": "Iscrizioni_Aperte_Open.json"
}

async def run_bot():
    print("--- [START] Avvio estrazione ISCRIZIONI APERTE ---")
    async with async_playwright() as p:
        # Aggiunto 'args' per maggiore compatibilità in ambienti cloud/headless
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Processo categoria: {cat_id}")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            try:
                await page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
                
                # --- FILTRO STATO ---
                await page.click('button[data-id="select_status"]')
                # Usiamo un approccio di clic diretto basato sul testo, più affidabile
                await page.get_by_role("option", name="Iscrizioni aperte").click()
                await asyncio.sleep(2)
                
                # --- FILTRI GEOGRAFICI ---
                await page.click('button[data-id="id_regioneSearch"]')
                await page.get_by_role("option", name="Lazio").click()
                await asyncio.sleep(2)
                
                await page.click('button[data-id="id_provinciaSearch"]')
                await page.get_by_role("option", name="Roma").click()
                await asyncio.sleep(2)
                
                # Selezione categoria
                await page.locator(f'a[data-id="{cat_id}"]').click()
                await asyncio.sleep(5)
                
                # Espansione lista
                print("-> Espansione lista tornei...")
                while True:
                    btn = page.locator("#btn-loadMore")
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(3)
                    else:
                        break
                
                # Recupero link tornei
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators if await loc.get_attribute("href")]))
                print(f"-> Trovati {len(links)} tornei.")
                
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    await page.goto(full_url, timeout=60000)
                    
                    try:
                        nome = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                    except:
                        nome = "Torneo senza nome"
                    
                    # Verifica PDF
                    download_btn = page.locator("#btnOrderGameDownload")
                    if await download_btn.is_visible():
                        # Non salviamo il PDF se non serve, verifichiamo solo la presenza
                        json_data["tornei"].append({"url": full_url, "nomeTorneo": nome.strip(), "status": "PDF presente"})
                    else:
                        json_data["tornei"].append({"url": full_url, "nomeTorneo": nome.strip(), "status": "Nessun PDF"})
                
                with open(filename, "w", encoding="utf-8") as f: 
                    json.dump(json_data, f, ensure_ascii=False, indent=4)
                    
            except Exception as e:
                print(f"Errore durante il processo: {e}")
            finally:
                await page.close()
            
        await browser.close()
    print("--- [END] Processo completato correttamente ---")

if __name__ == "__main__": 
    asyncio.run(run_bot())
