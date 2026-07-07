import asyncio
import json
import sys
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio del bot ---")
    
    async with async_playwright() as p:
        # headless=True è obbligatorio su GitHub Actions
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        
        print("--- Navigazione verso il sito FITP ---")
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        
        print("--- Impostazione filtri (Iscrizioni Aperte, Lazio) ---")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
        
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        
        await page.keyboard.press("Enter")
        await asyncio.sleep(5) # Attesa generosa per il caricamento risultati
        
        # Estrazione link tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        urls = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"--- Trovati {len(urls)} tornei. Inizio analisi. ---")
        
        risultati = []
        
        for idx, url in enumerate(urls, 1):
            full_url = f"https://www.fitp.it{url}"
            print(f"[{idx}/{len(urls)}] Analisi Torneo: {full_url}")
            
            await page.goto(full_url, wait_until="networkidle")
            
            # Conta quante categorie (box) ci sono
            dettagli = page.locator("a:has-text('Dettaglio >')")
            count = await dettagli.count()
            print(f"    -> Trovate {count} categorie in questo torneo.")
            
            for i in range(count):
                # Ricarichiamo i riferimenti dei bottoni per evitare errori di pagina
                btn = page.locator("a:has-text('Dettaglio >')").nth(i)
                await btn.click()
                await page.wait_for_load_state("networkidle")
                print(f"    -> Entrato nella categoria {i+1}")
                
                # Estrai giocatori
                giocatori = await page.locator("a[href*='Pagina-Giocatore']").all()
                print(f"       Trovati {len(giocatori)} giocatori.")
                
                for j, g_link in enumerate(giocatori, 1):
                    g_url = await g_link.get_attribute("href")
                    await page.goto(f"https://www.fitp.it{g_url}", wait_until="domcontentloaded")
                    
                    nome = await page.locator("span#spn-tournament-description").text_content()
                    nome_pulito = nome.strip()
                    print(f"       [{j}/{len(giocatori)}] Giocatore: {nome_pulito}")
                    
                    risultati.append({"torneo": full_url, "nome": nome_pulito})
                    
                    # Torna indietro alla lista della categoria
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
                
                # Torna al dettaglio del torneo principale per passare alla categoria successiva
                await page.goto(full_url, wait_until="networkidle")
        
        # Salvataggio finale
        print("--- Estrazione terminata. Scrittura file JSON... ---")
        with open("Risultati_Iscrizioni.json", "w", encoding="utf-8") as f:
            json.dump(risultati, f, ensure_ascii=False, indent=4)
            
        print("--- [END] Processo completato con successo ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
