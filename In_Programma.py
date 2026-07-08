import asyncio
import json
import sys
from playwright.async_api import async_playwright

# Forza l'output immediato per vedere i progressi nei log
sys.stdout.reconfigure(line_buffering=True)

async def run_bot():
    print("--- [START] Avvio Bot FITP Versione 2026 ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Forza una risoluzione standard per evitare che i menu cadano fuori schermo
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(60000) 

        print("--- [DEBUG] Navigazione sito ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        
        # 1. Filtri (Gestione Bootstrap Select)
        print("--- [DEBUG] Applicazione filtri ---")
        for filter_btn, option_text in [
            ('button[data-id="select_status"]', "In programma"),
            ('button[data-id="id_regioneSearch"]', "Lazio"),
            ('button[data-id="id_provinciaSearch"]', "Roma")
        ]:
            await page.locator(filter_btn).click()
            # Clicca l'opzione basata sul testo
            await page.locator(f'span:text-is("{option_text}")').last.click()
            await asyncio.sleep(1)
            
        await page.locator('button:text("Cerca")').click()
        await asyncio.sleep(5)
        
        # 2. Caricamento risultati
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await asyncio.sleep(2)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        print(f"--- [INFO] Trovati {len(urls)} tornei ---")
        
        dati_giov, dati_open = {"tornei": []}, {"tornei": []}
        
        for idx, url in enumerate(urls):
            full_url = f"https://www.fitp.it{url}"
            try:
                await page.goto(full_url, wait_until="domcontentloaded")
                
                # Cerchiamo i bottoni "Dettaglio"
                dettagli = page.locator("span:has-text('Dettaglio >')")
                count = await dettagli.count()
                
                if count > 0:
                    for i in range(count):
                        # Clicchiamo e aspettiamo che la pagina si aggiorni
                        btn = page.locator("span:has-text('Dettaglio >')").nth(i)
                        await btn.click()
                        
                        # Estrazione intelligente: invece di h1, prendiamo tutto il contenitore
                        # .cc-title-main è il titolo, .cc-content-value sono i nomi
                        categoria = await page.locator(".cc-title-main").first.text_content()
                        giocatori = await page.locator(".cc-content-value").all_text_contents()
                        
                        lista_nomi = [g.strip() for g in giocatori if g.strip()]
                        entry = {"torneo": url, "categoria": (categoria or "N/A").strip(), "iscritti": lista_nomi}
                        
                        if any(x in (categoria or "") for x in ["Under", "Giovanile", "U10", "U12", "U14", "U16"]):
                            dati_giov["tornei"].append(entry)
                        else:
                            dati_open["tornei"].append(entry)
                        
                        await page.go_back(wait_until="domcontentloaded")
                
                print(f"--- [PROGRESSO] Analizzati {idx+1}/{len(urls)} ---")
                    
            except Exception as e:
                print(f"--- [ERRORE] su {url}: {e} ---")
                continue
        
        # 3. Salvataggio
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
