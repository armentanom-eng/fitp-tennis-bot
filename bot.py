import asyncio
import os
import json
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("--- Navigazione portale tornei ---")
        await page.goto(BASE_URL, wait_until="networkidle")
        
        # 1. Filtri (usando la logica che funziona nel tuo codice)
        await page.click('button[data-id="select_status"]')
        await asyncio.sleep(1)
        await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
        
        await page.click('button[data-id="id_regioneSearch"]')
        await asyncio.sleep(1)
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        
        await page.keyboard.press("Enter")
        await asyncio.sleep(3)
        
        # 2. Caricamento tornei
        while await page.locator("#btn-loadMore").is_visible():
            await page.click("#btn-loadMore")
            await asyncio.sleep(2)
            
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei ---")
        
        risultati = []
        
        # 3. Analisi Dettaglio
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            print(f"-> Analizzo: {full_url}")
            await page.goto(full_url, wait_until="networkidle")
            
            # Tab categorie
            tabs = await page.locator("a[data-toggle='tab']").all()
            for tab in tabs:
                cat_name = await tab.text_content()
                await tab.click()
                await asyncio.sleep(1)
                
                # Estrazione Giocatori
                giocatori = await page.locator("#players a[href*='Pagina-Giocatore']").all()
                for g_link in giocatori:
                    g_url = await g_link.get_attribute("href")
                    
                    # Vai alla scheda giocatore
                    await page.goto(f"https://www.fitp.it{g_url}")
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    
                    risultati.append({
                        "torneo": full_url,
                        "categoria": cat_name.strip(),
                        "nome": nome.strip()
                    })
                    print(f"   + Estratto: {nome.strip()}")
                    await page.go_back()
                    # Ritorna alla tab corretta se necessario
                    await page.goto(full_url)
                    await tab.click() 

        with open("Iscrizioni_Finali.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        print("--- Estrazione completata ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
