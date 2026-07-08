import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Deep Scraper - Struttura Gerarchica ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = await context.new_page()
        
        # ... (stessa navigazione e caricamento tornei del codice precedente) ...
        # (Omissis per brevità, usa la navigazione del codice precedente)

        for url in unique_urls:
            try:
                await page.goto(url)
                await asyncio.sleep(3)
                nome_torneo = await page.evaluate('document.querySelector(".cc-title-main")?.innerText.trim() || "Torneo"')
                
                bottoni = await page.query_selector_all('text=Dettaglio >')
                tabelloni_dati = []
                
                for i in range(len(bottoni)):
                    btns = await page.query_selector_all('text=Dettaglio >')
                    # Estrai il nome della categoria (es. Singolare Maschile)
                    nome_categoria = await btns[i].evaluate("el => el.parentElement.innerText.split('\\n')[0].trim()")
                    
                    await btns[i].click()
                    await asyncio.sleep(2)
                    
                    nomi = await page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('.cc-content-value'))
                                    .map(el => el.innerText.trim())
                                    .filter(t => t.length > 5 && /^[A-Z\s'À-ÖØ-öø-ÿ]+$/.test(t));
                    }""")
                    
                    tabelloni_dati.append({
                        "categoria": nome_categoria,
                        "iscritti": sorted(list(set(nomi)))
                    })
                    
                    await page.go_back()
                    await asyncio.sleep(2)
                
                # Creazione entry strutturata
                entry = {"torneo": nome_torneo, "dettagli": tabelloni_dati}
                
                # ... (Logica di suddivisione Giovanili/Open) ...
            except: continue
        # ... (Salvataggio JSON) ...
