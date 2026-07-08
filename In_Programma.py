import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio Bot In Programma Unificato ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        # 1. Configurazione Filtri
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        # 2. Caricamento lista
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await asyncio.sleep(2)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        dati_giov, dati_open = {"tornei": []}, {"tornei": []}
        
        # 3. Analisi Tornei
        for url in urls:
            full_url = f"https://www.fitp.it{url}"
            await page.goto(full_url, wait_until="networkidle")
            
            # Troviamo quanti bottoni "Dettaglio" ci sono
            # Usiamo un selettore più generico che funziona meglio
            dettagli = page.locator("span:has-text('Dettaglio >')")
            count = await dettagli.count()
            
            for i in range(count):
                try:
                    # Ricarichiamo la pagina per resettare lo stato ad ogni iterazione (fondamentale)
                    await page.goto(full_url, wait_until="networkidle")
                    btn = page.locator("span:has-text('Dettaglio >')").nth(i)
                    
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await page.wait_for_load_state("networkidle")
                        
                        categoria = await page.locator("h1.cc-title-main").first.text_content()
                        # ESTRAZIONE TESTO GENERICA (funziona meglio dei link specifici)
                        # Prende tutto il testo all'interno dei box dei giocatori
                        giocatori = await page.locator(".cc-content-value").all_text_contents()
                        
                        # Pulizia nomi
                        lista_nomi = [g.strip() for g in giocatori if g.strip()]
                        
                        entry = {"torneo": url, "categoria": categoria.strip(), "iscritti": lista_nomi}
                        
                        if any(x in categoria for x in ["Under", "Giovanile", "U10", "U11", "U12", "U14", "U16"]):
                            dati_giov["tornei"].append(entry)
                        else:
                            dati_open["tornei"].append(entry)
                            
                except Exception as e:
                    print(f"--- [ERRORE] su categoria {i}: {e} ---")
                    continue
        
        # 4. Salvataggio
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- [END] Processo completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
