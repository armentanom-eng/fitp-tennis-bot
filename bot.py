import asyncio
import json
import os
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
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0")
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Processo categoria: {cat_id}")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            try:
                await page.goto(BASE_URL, timeout=60000)
                
                # 1. Gestione Cookie: Chiudiamo il banner se esiste
                try:
                    await page.wait_for_selector('button:has-text("Accetto")', timeout=5000)
                    await page.click('button:has-text("Accetto")')
                except: pass

                # 2. Filtri: usiamo l'esecuzione JS per forzare l'apertura dei menu
                # Questo evita il timeout del .dropdown-menu.show
                def force_select(btn_id, option_text):
                    return f"""
                    (async () => {{
                        const btn = document.querySelector('button[data-id="{btn_id}"]');
                        btn.click();
                        await new Promise(r => setTimeout(r, 1000));
                        const items = Array.from(document.querySelectorAll('.dropdown-menu.show li a'));
                        const target = items.find(el => el.innerText.includes("{option_text}"));
                        if (target) target.click();
                    }})()
                    """

                await page.evaluate(force_select("select_status", "Iscrizioni aperte"))
                await asyncio.sleep(2)
                await page.evaluate(force_select("id_regioneSearch", "Lazio"))
                await asyncio.sleep(2)
                await page.evaluate(force_select("id_provinciaSearch", "Roma"))
                await asyncio.sleep(2)
                
                # Selezione categoria (link diretto)
                await page.locator(f'a[data-id="{cat_id}"]').click()
                await asyncio.sleep(5)
                
                # Espansione lista
                while True:
                    btn = page.locator("#btn-loadMore")
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(3)
                    else: break
                
                # Estrazione
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                
                for link in links:
                    await page.goto(f"https://www.fitp.it{link}", timeout=60000)
                    try:
                        nome = await page.locator("h1.cc-title-main").inner_text()
                        has_pdf = await page.locator("#btnOrderGameDownload").is_visible()
                        json_data["tornei"].append({"url": f"https://www.fitp.it{link}", "nomeTorneo": nome.strip(), "status": "PDF presente" if has_pdf else "No PDF"})
                    except: continue
                
                with open(filename, "w", encoding="utf-8") as f: 
                    json.dump(json_data, f, ensure_ascii=False, indent=4)
                    
            except Exception as e: print(f"Errore {cat_id}: {e}")
            finally: await page.close()
            
        await browser.close()

if __name__ == "__main__": 
    asyncio.run(run_bot())
