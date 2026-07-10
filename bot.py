import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

# Nomi file definiti
CATEGORIES = {
    "t_giovanili": "Iscrizioni_Aperte_Giovanili.json", 
    "t_affiliati": "Iscrizioni_Aperte_Open.json"
}

async def run_bot():
    print("--- [START] Avvio estrazione ISCRIZIONI APERTE ---")
    print(f"Directory di lavoro: {os.getcwd()}")
    
    async with async_playwright() as p:
        # Configurazione browser per ambienti headless (GitHub Actions)
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Processo categoria: {cat_id}")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            try:
                await page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
                
                # --- FILTRI ---
                # Stato
                await page.click('button[data-id="select_status"]')
                await page.get_by_role("option", name="Iscrizioni aperte").click()
                await asyncio.sleep(2)
                
                # Regione
                await page.click('button[data-id="id_regioneSearch"]')
                await page.get_by_role("option", name="Lazio").click()
                await asyncio.sleep(2)
                
                # Provincia
                await page.click('button[data-id="id_provinciaSearch"]')
                await page.get_by_role("option", name="Roma").click()
                await asyncio.sleep(2)
                
                # Selezione categoria (es. t_giovanili)
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
                
                # Recupero link
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
                    
                    # Verifica presenza PDF
                    download_btn = page.locator("#btnOrderGameDownload")
                    status = "PDF presente" if await download_btn.is_visible() else "Nessun PDF"
                    
                    json_data["tornei"].append({"url": full_url, "nomeTorneo": nome.strip(), "status": status})
                
                # --- SALVATAGGIO ROBUSTO ---
                output_path = os.path.join(os.getcwd(), filename)
                with open(output_path, "w", encoding="utf-8") as f: 
                    json.dump(json_data, f, ensure_ascii=False, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                
                print(f"-> File creato con successo: {output_path}")
                    
            except Exception as e:
                print(f"Errore critico durante il processo di {cat_id}: {e}")
            finally:
                await page.close()
            
        await browser.close()
    print("--- [END] Processo completato ---")

if __name__ == "__main__": 
    asyncio.run(run_bot())
