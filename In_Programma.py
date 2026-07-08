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
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()
        
        # Navigazione
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="domcontentloaded")
        await page.click('button[data-id="select_status"]')
        await page.locator('span:text-is("In programma")').last.click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.locator('span:text-is("Lazio")').last.click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.locator('span:text-is("Roma")').last.click()
        await page.click('#btn-search')
        await asyncio.sleep(5)

        urls = await page.evaluate('Array.from(document.querySelectorAll("a[href*=\'Dettaglio-Competizione\']")).map(a => a.href)')
        urls = list(set(urls))
        
        dati_giov, dati_open = [], []
        
        for url in urls:
            try:
                log(f"Analizzo: {url[-10:]}")
                await page.goto(url, wait_until="domcontentloaded")
                
                # Prendiamo tutti i bottoni dettaglio
                dettagli = page.locator("text=Dettaglio >")
                count = await dettagli.count()
                
                for i in range(count):
                    btn = page.locator("text=Dettaglio >").nth(i)
                    await btn.click()
                    await asyncio.sleep(3) # Pausa fissa per vedere la schermata
                    
                    # --- LETTURA TOTALE ---
                    # Invece di cercare tag, leggiamo il corpo della pagina
                    testo_pagina = await page.evaluate("document.body.innerText")
                    cat = await page.locator("h1.cc-title-main").first.text_content()
                    
                    # Salviamo tutto il contenuto trovato
                    entry = {
                        "torneo": url, 
                        "categoria": cat.strip() if cat else "N/A", 
                        "testo_grezzo": testo_pagina[:500] # Prendiamo un estratto per sicurezza
                    }
                    
                    if any(k in entry["categoria"].lower() for k in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                        dati_giov.append(entry)
                    else:
                        dati_open.append(entry)
                    
                    await page.go_back()
                    await asyncio.sleep(2)
            except Exception as e:
                log(f"Errore su {url}: {e}")
                continue

        with open("Iscritti_Giovanili.json", "w", encoding="utf-8") as f: json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open.json", "w", encoding="utf-8") as f: json.dump(dati_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        log("Finito")

if __name__ == "__main__":
    asyncio.run(run_bot())
