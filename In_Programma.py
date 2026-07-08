import asyncio
import json
import sys
import os
from playwright.async_api import async_playwright

# Forza l'output immediato su terminale/log
sys.stdout.reconfigure(line_buffering=True)

async def run_bot():
    print("--- [START] Avvio Bot Debugging Versione 2026 ---")
    
    async with async_playwright() as p:
        print("--- [DEBUG] Playwright inizializzato ---")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        page.set_default_timeout(60000) 

        print("--- [DEBUG] Navigazione sito FITP ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        
        # Filtri
        print("--- [DEBUG] Impostazione filtri ---")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        print("--- [DEBUG] Caricamento lista completa ---")
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await asyncio.sleep(2)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        print(f"--- [INFO] Trovati {len(urls)} tornei ---")
        
        dati_giov, dati_open = {"tornei": []}, {"tornei": []}
        count_analizzati = 0
        
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            try:
                await page.goto(full_url, wait_until="domcontentloaded")
                dettagli = page.locator("span:has-text('Dettaglio >')")
                count = await dettagli.count()
                
                for i in range(count):
                    btn = page.locator("span:has-text('Dettaglio >')").nth(i)
                    await btn.click()
                    await page.locator("h1.cc-title-main").first.wait_for()
                    
                    categoria = await page.locator("h1.cc-title-main").first.text_content()
                    giocatori = await page.locator(".cc-content-value").all_text_contents()
                    lista_nomi = [g.strip() for g in giocatori if g.strip()]
                    
                    entry = {"torneo": url, "categoria": categoria.strip(), "iscritti": lista_nomi}
                    if any(x in categoria for x in ["Under", "Giovanile", "U10", "U12", "U14", "U16"]):
                        dati_giov["tornei"].append(entry)
                    else:
                        dati_open["tornei"].append(entry)
                    
                    await page.go_back(wait_until="domcontentloaded")
                
                count_analizzati += 1
                if count_analizzati % 5 == 0 or count_analizzati == len(urls):
                    print(f"--- [PROGRESSO] {count_analizzati}/{len(urls)} tornei analizzati ---")
                    
            except Exception as e:
                print(f"--- [ERRORE] Errore su {url}: {e} ---")
                continue
        
        print("--- [DEBUG] Salvataggio dati ---")
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
