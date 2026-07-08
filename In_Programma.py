import asyncio
import json
import sys
from playwright.async_api import async_playwright

def log(msg):
    print(f"--- {msg} ---")
    sys.stdout.flush()

async def run_bot():
    log("Inizio esecuzione")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        log("Navigazione FITP")
        try:
            await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded", timeout=60000)
            log("Pagina caricata")
        except Exception as e:
            log(f"Errore caricamento: {e}")
            return

        log("Clicco filtri")
        try:
            await page.click('button[data-id="select_status"]')
            await page.locator('span:text-is("In programma")').last.click()
            await page.click('button[data-id="id_regioneSearch"]')
            await page.locator('span:text-is("Lazio")').last.click()
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.locator('span:text-is("Roma")').last.click()
            await page.click('#btn-search')
            await asyncio.sleep(5)
            log("Ricerca eseguita")
        except Exception as e:
            log(f"Errore filtri: {e}")
            return

        log("Estrazione link")
        urls = await page.evaluate('Array.from(document.querySelectorAll("a[href*=\'Dettaglio-Competizione\']")).map(a => a.href)')
        urls = list(set(urls))
        log(f"Trovati {len(urls)} tornei")

        dati_giov, dati_open = [], []
        
        for url in urls:
            try:
                log(f"Analizzo: {url[-10:]}")
                await page.goto(url, wait_until="domcontentloaded")
                
                # Attesa per il caricamento dei bottoni Dettaglio
                await page.wait_for_selector("text=Dettaglio >", timeout=60000)
                dettagli = page.locator("text=Dettaglio >")
                count = await dettagli.count()
                
                for i in range(count):
                    # Recuperiamo di nuovo il bottone per sicurezza
                    btn = page.locator("text=Dettaglio >").nth(i)
                    
                    # Aspettiamo che sia cliccabile
                    await btn.wait_for(state="visible", timeout=60000)
                    await btn.click()
                    
                    # Aspettiamo il caricamento effettivo dei dati
                    await page.wait_for_selector(".cc-content-value", timeout=60000)
                    
                    cat = await page.locator("h1.cc-title-main").first.text_content()
                    nomi = await page.evaluate("""() => Array.from(document.querySelectorAll('.cc-content-value'))
                        .map(el => el.innerText.trim())
                        .filter(t => t.length > 3)""")
                    
                    entry = {"torneo": url, "categoria": cat.strip(), "iscritti": sorted(list(set(nomi)))}
                    if any(k in cat.lower() for k in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                        dati_giov.append(entry)
                    else:
                        dati_open.append(entry)
                    
                    # Torniamo alla pagina del torneo per la prossima categoria
                    await page.goto(url, wait_until="domcontentloaded")
            except Exception as e:
                log(f"Errore su torneo: {e}")
                continue

        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        log("Finito")

if __name__ == "__main__":
    asyncio.run(run_bot())
