import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # User-agent simulato per non farsi bloccare
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei")
        await asyncio.sleep(6) # Aspetta il caricamento iniziale
        
        # Recupero link tornei
        urls = await page.evaluate('Array.from(document.querySelectorAll("a[href*=\'Dettaglio-Competizione\']")).map(a => a.href)')
        unique_urls = list(set(urls))
        print(f"--- [INFO] Analisi di {len(unique_urls)} tornei ---")
        
        data_giov, data_open = [], []
        
        for url in unique_urls:
            try:
                await page.goto(url)
                await asyncio.sleep(4) # Pausa di sicurezza per il caricamento contenuto
                
                # Nome torneo: forza la lettura precisa del titolo principale
                nome_torneo = await page.evaluate('document.querySelector("h1.cc-title-main") ? document.querySelector("h1.cc-title-main").innerText.trim() : "Torneo Sconosciuto"')
                
                # Estrazione Nomi (Filtro Anti-Numeri/Date/Ranking)
                nomi = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('.cc-content-value'))
                                .map(el => el.innerText.trim())
                                .filter(t => t.length > 3 && t === t.toUpperCase() && !t.includes('PDF') && !t.includes('€') && !t.includes('/') && !/^[\\d.,\\s]+$/.test(t));
                }""")
                
                # Pulizia iscritti
                iscritti_puliti = sorted(list(set(nomi)))
                entry = {"torneo": nome_torneo, "iscritti": iscritti_puliti}
                
                # Categorizzazione
                if any(kw in nome_torneo.lower() for kw in ["under", "u10", "u12", "u14", "u16", "giovanile"]):
                    data_giov.append(entry)
                else:
                    data_open.append(entry)
                
                print(f"--- [OK] {nome_torneo[:40]}... ({len(iscritti_puliti)} iscritti) ---")
                    
            except Exception as e:
                print(f"--- [ERRORE] su {url}: {e} ---")
                continue

        # Salvataggio file
        with open("Iscritti_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(data_open, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        print("--- [END] Processo completato. File generati correttamente. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())