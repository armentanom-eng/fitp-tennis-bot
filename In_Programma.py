import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Filtri (usiamo la forza bruta di Playwright invece di JS fallibile)
        # Clicca il tasto stato
        await page.locator('button[data-id="select_status"]').click()
        # Clicca l'opzione (cerca il testo specifico)
        await page.locator('span', has_text="In programma").click()
        await asyncio.sleep(2)
        
        # Clicca tasto cerca
        await page.locator('#btn-search').click()
        await asyncio.sleep(5)
        
        # Otteniamo gli URL
        urls = await page.evaluate("() => Array.from(document.querySelectorAll('a[href*=\"Dettaglio-Competizione\"]')).map(a => a.href)")
        unique_urls = list(set(urls))
        
        data_giov, data_open = [], []

        for url in unique_urls:
            try:
                await page.goto(url)
                await asyncio.sleep(3)
                
                # Estrazione dati in JavaScript nativo (compatibile)
                risultato = await page.evaluate("""() => {
                    const titoli = document.querySelectorAll('.cc-content-value');
                    const nomi = Array.from(titoli).map(el => el.innerText.trim());
                    const titoloTorneo = document.querySelector('h1')?.innerText || 'Sconosciuto';
                    return { titolo: titoloTorneo, partecipanti: nomi.filter(n => n.length > 3 && !n.includes('pdf')) };
                }""")
                
                entry = {"torneo": risultato['titolo'], "iscritti": list(set(risultato['partecipanti']))}
                
                if "under" in risultato['titolo'].lower():
                    data_giov.append(entry)
                else:
                    data_open.append(entry)
                    
            except Exception:
                continue

        with open("Iscritti_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
