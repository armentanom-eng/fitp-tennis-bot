import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigazione semplificata
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        await asyncio.sleep(5)
        
        # Filtri base (usiamo JS puro per sicurezza)
        await page.evaluate("""() => {
            document.querySelectorAll('button[data-id="select_status"]')[0].click();
        }""")
        await asyncio.sleep(1)
        await page.evaluate("""() => {
            document.querySelectorAll('span:contains("In programma")')[0].click();
        }""")
        # (Aggiungi qui gli altri filtri se necessari, ma teniamolo semplice per ora)
        
        await page.evaluate('document.getElementById("btn-search").click()')
        await asyncio.sleep(5)
        
        # Estrazione URL senza complicazioni
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href*="Dettaglio-Competizione"]'))
                        .map(a => a.href);
        }""")
        
        unique_urls = list(set(links))
        print(f"Trovati {len(unique_urls)} tornei")

        data_giov, data_open = [], []

        for url in unique_urls:
            try:
                await page.goto(url)
                await asyncio.sleep(3)
                
                # Estrazione testuale pura: ignoriamo bottoni e clic
                # Prendiamo solo i nomi dei giocatori tramite i selettori CSS
                nomi = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('.cc-content-value'))
                                .map(el => el.innerText.trim())
                                .filter(text => text.length > 3 && !text.includes('pdf') && !text.includes('€'));
                }""")
                
                nome_torneo = await page.evaluate('document.querySelector("h1")?.innerText || "Sconosciuto"')
                
                entry = {"torneo": nome_torneo, "iscritti": list(set(nomi))}
                
                if "under" in nome_torneo.lower():
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
