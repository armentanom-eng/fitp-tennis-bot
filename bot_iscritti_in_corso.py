import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- Avvio estrazione ISCRITTI (Metodo Tabella) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Dizionario per gestire le due categorie
        categorie_da_cercare = {
            "t_giovanili": "Iscritti_Giovanili.json",
            "t_affiliati": "Iscritti_Open.json"
        }

        for cat_data_id, nome_file in categorie_da_cercare.items():
            print(f"-> Analisi categoria: {nome_file}")
            risultati = {"tornei": []}
            
            # Naviga e applica filtri
            await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
            
            # Filtro Stato
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name="In corso").click()
            
            # Filtro Regione
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            
            # Categoria
            await page.locator(f'a[data-id="{cat_data_id}"]').first.click()
            await asyncio.sleep(5)
            
            # Recupera URL tornei
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            urls = list(set([await loc.get_attribute("href") for loc in locators]))
            
            for url in urls:
                full_url = f"https://www.fitp.it{url}"
                try:
                    await page.goto(full_url, wait_until="domcontentloaded")
                    nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                    print(f"  Analizzo: {nome_torneo.strip()}")
                    
                    count = await page.locator("text=Dettaglio >").count()
                    for i in range(count):
                        try:
                            # Ritorna alla pagina del torneo per ogni bottone
                            await page.goto(full_url, wait_until="domcontentloaded")
                            btn = page.locator("text=Dettaglio >").nth(i)
                            
                            if await btn.is_visible():
                                await btn.click(force=True)
                                
                                # Attesa sicura della tabella
                                try:
                                    await page.wait_for_selector("table", timeout=10000)
                                except:
                                    print(f"    ! Tabella non trovata per tabellone {i+1}, salto...")
                                    continue
                                
                                await asyncio.sleep(2)
                                tabellone = await page.locator("span#spn-tournament-description").text_content() or "N/A"
                                
                                # Lettura righe iscritti
                                rows = page.locator("table tbody tr")
                                nomi = []
                                for r in range(await rows.count()):
                                    riga_testo = await rows.nth(r).text_content()
                                    if riga_testo and len(riga_testo.strip()) > 3:
                                        nomi.append(riga_testo.strip())
                                
                                risultati["tornei"].append({
                                    "nome": f"{nome_torneo.strip()} - {tabellone.strip()}",
                                    "iscritti": list(set(nomi))
                                })
                        except Exception as e:
                            print(f"    ! Errore nel dettaglio {i+1}: {e}")
                            continue
                except Exception as e:
                    print(f"  ! Errore critico sul torneo {url}: {e}")
            
            with open(nome_file, "w", encoding="utf-8") as f:
                json.dump(risultati, f, ensure_ascii=False, indent=4)
        
        await browser.close()
        print("--- [END] Processo completato. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
