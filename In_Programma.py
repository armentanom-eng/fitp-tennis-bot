import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio Bot Difensivo ---")
    async with async_playwright() as p:
        # Browser configurato per essere più veloce e meno sensibile
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()
        
        # Timeout globale per evitare blocchi infiniti
        page.set_default_timeout(10000) 
        
        try:
            await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
            await page.click('button[data-id="select_status"]')
            await page.locator('span:text-is("In programma")').last.click()
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.locator('span:text-is("Roma")').last.click()      
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            urls = list(set([await loc.get_attribute("href") for loc in locators]))
            print(f"--- Trovati {len(urls)} tornei. ---")
            
            for url in urls:
                print(f"--- Analizzo: {url[-10:]} ---")
                try:
                    await page.goto(f"https://www.fitp.it{url}", wait_until="domcontentloaded")
                    
                    # Se appare il pop-up, lo saltiamo immediatamente
                    if await page.locator("text=non e' al momento disponibile").is_visible():
                        print("    -> Pop-up rilevato, skip.")
                        continue
                    
                    # Trova solo i bottoni davvero cliccabili
                    tutti_i_bottoni = page.locator("text=Dettaglio >")
                    count = await tutti_i_bottoni.count()
                    
                    for i in range(count):
                        btn = tutti_i_bottoni.nth(i)
                        if await btn.is_visible():
                            try:
                                await btn.click(timeout=5000)
                                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                                # ... estrazione dati ...
                                await page.go_back()
                                await page.wait_for_load_state("domcontentloaded")
                            except:
                                print(f"    ! Errore clic su bottone {i}")
                                await page.goto(f"https://www.fitp.it{url}")
                                
                except Exception as e:
                    print(f"    ! Salto torneo causa errore: {e}")
                    
        finally:
            await browser.close()
            print("--- [END] Processo terminato. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
