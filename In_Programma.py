import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Scraper Definitivo - Caricamento Completo ---")
    
    async with async_playwright() as p:
        # Browser configurato per sembrare umano
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        # 1. Navigazione
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        await asyncio.sleep(5)
        
        # Applicazione filtri
        print("--- [INFO] Applicazione filtri...")
        # (Logica semplificata per cliccare i menu dei filtri)
        await page.locator('button[data-id="select_status"]').click()
        await page.locator('span:text-is("In programma")').last.click()
        await asyncio.sleep(1)
        await page.locator('button[data-id="id_regioneSearch"]').click()
        await page.locator('span:text-is("Lazio")').last.click()
        await asyncio.sleep(1)
        await page.locator('button[data-id="id_provinciaSearch"]').click()
        await page.locator('span:text-is("Roma")').last.click()
        await asyncio.sleep(1)
        
        await page.locator('#btn-search').click()
        await asyncio.sleep(5)
        
        # 2. Caricamento dinamico: "Carica altro"
        print("--- [INFO] Caricamento totale lista tornei in corso... ---")
        while True:
            load_more_btn = await page.query_selector('button#btn-loadMore')
            if load_more_btn and await load_more_btn.is_visible():
                await load_more_btn.click()
                await asyncio.sleep(3)
                print("--- [INFO] Caricati altri tornei... ---")
            else:
                break
        
        # Recupero URL
        urls = await page.evaluate('Array.from(document.querySelectorAll("a[href*=\'Dettaglio-Competizione\']")).map(a => a.href)')
        unique_urls = list(set(urls))
        print(f"--- [INFO] Trovati {len(unique_urls)} tornei totali. Analisi in corso... ---")
        
        data_giov, data_open = [], []
        
        # 3. Analisi tornei
        for url in unique_urls:
            try:
                await page.goto(url)
                await asyncio.sleep(4)
                
                # Nome torneo specifico
                nome_torneo = await page.evaluate('document.querySelector("h1.cc-title-main") ? document.querySelector("h1.cc-title-main").innerText.trim() : "Torneo"')
                
                # Estrazione nomi pulita (esclude ranking come 4.5 e scritte di sistema)
                nomi = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('.cc-content-value'))
                                .map(el => el.innerText.trim())
                                .filter(t => t.length > 3 && t === t.toUpperCase() && !t.includes('PDF') && !t.includes('€') && !t.includes('/') && !/^[\\d.,\\s]+$/.test(t));
                }""")
                
                iscritti_puliti = sorted(list(set(nomi)))
                entry = {"torneo": nome_torneo, "iscritti": iscritti_puliti}
                
                if any(kw in nome_torneo.lower() for kw in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                    data_giov.append(entry)
                else:
                    data_open.append(entry)
                
                print(f"--- [OK] Analizzato: {nome_torneo[:30]}... ({len(iscritti_puliti)} iscritti) ---")
                    
            except Exception as e:
                continue

        # 4. Salvataggio
        with open("Iscritti_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        print("--- [END] Processo completato: file JSON aggiornati con tutti i tornei ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
