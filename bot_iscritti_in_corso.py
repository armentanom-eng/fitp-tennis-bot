import asyncio
import pdfplumber
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

CATEGORIES = {
    "t_giovanili": "Giovanili_Partite_incorsopdf.json", 
    "t_affiliati": "Open_Partite_incorsopdf.json"
}

async def run_bot():
    print("--- [START] Avvio modalità Human-Mimic ---")
    async with async_playwright() as p:
        # Aggiungiamo un User-Agent reale per sembrare un vero browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        for cat_id, filename in CATEGORIES.items():
            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            
            # USO DI JAVASCRIPT PURO PER I CLICK
            # Questo bypassa quasi tutte le logiche di visibilità/timeout
            try:
                # Seleziona "In corso"
                await page.evaluate('document.querySelector("button[data-id=\'select_status\']").click()')
                await asyncio.sleep(2)
                await page.evaluate('document.querySelector("a[role=\'option\'][data-tokens*=\'In corso\']").click()')
                await asyncio.sleep(2)
                
                # Seleziona Lazio
                await page.evaluate('document.querySelector("button[data-id=\'id_regioneSearch\']").click()')
                await asyncio.sleep(2)
                await page.evaluate('document.querySelector("a[role=\'option\'][data-tokens*=\'Lazio\']").click()')
                await asyncio.sleep(2)
                
                # Seleziona Roma
                await page.evaluate('document.querySelector("button[data-id=\'id_provinciaSearch\']").click()')
                await asyncio.sleep(2)
                await page.evaluate('document.querySelector("a[role=\'option\'][data-tokens*=\'Roma\']").click()')
                await asyncio.sleep(5)
                
                # Categoria
                await page.evaluate(f'document.querySelector("a[data-id=\'{cat_id}\']").click()')
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Errore nella selezione filtri JS: {e}")
                await page.screenshot(path="debug_error.png") # Salva una foto per vedere cosa succede
                continue

            # (Procedi con la logica di estrazione...)
            print("Filtri applicati correttamente via JS.")
            await page.close()
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
