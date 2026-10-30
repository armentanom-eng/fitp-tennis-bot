import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

# Mappa delle categorie con i file di output dedicati per l'app
CATEGORIES = {
    "t_giovanili": "Iscritti_Giovanili_In_Programma.json", 
    "t_affiliati": "Iscritti_Open_In_Programma.json"
}

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

async def run_bot():
    print("--- [START] Avvio estrazione WEB (Tornei 'In Programma' - Resiliente) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(60000)
        
        # Iteriamo sulle categorie
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Elaborazione categoria: {cat_id}")
            dati_categoria = {"tornei": []}
            
            # Apertura pagina principale con retry
            successo_avvio = False
            for t_avvio in range(3):
                try:
                    await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    successo_avvio = True
                    break
                except Exception as e:
                    print(f"-> [Warning] Tentativo {t_avvio+1} apertura BASE_URL fallito: {e}")
                    await asyncio.sleep(5)
            
            if not successo_avvio:
                print(f"-> [Errore] Impossibile raggiungere {BASE_URL}. Salto categoria.")
                continue
            
            # --- 1. FILTRI BASE ---
            print("-> Seleziono Stato: In programma...")
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
            await asyncio.sleep(12)
            
            print("-> Seleziono Regione: Lazio...")
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(12)
            
            print("-> Seleziono Provincia: Roma...")
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(12)
            
            # --- IMPOSTAZIONE DATA INIZIO (OGGI) E SVUOTAMENTO DATA FINE ---
            oggi = datetime.now()
            data_inizio = oggi.strftime("%d/%m/%Y") 
            
            print(f"-> [STEP DATA] Imposto Data Inizio: {data_inizio} | Data Fine: [VUOTA]")
            
            await page.evaluate(f"""() => {{
                const start = document.querySelector('#dpk_start_date');
                const end = document.querySelector('#dpk_end_date');
                
                if(start) {{
                    start.removeAttribute('min');
                    start.removeAttribute('max');
                    start.value = "{data_inizio}";
                    if (window.jQuery && jQuery(start).data('datepicker')) {{
                        jQuery(start).datepicker('setStartDate', null);
                        jQuery(start).datepicker('setDate', '{data_inizio}');
                    }}
                    start.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    start.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                
                if(end) {{
                    end.removeAttribute('min');
                    end.removeAttribute('max');
                    end.value = ""; 
                    if (window.jQuery && jQuery(end).data('datepicker')) {{
                        jQuery(end).datepicker('setDate', null);
                    }}
                    end.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    end.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""")
            await asyncio.sleep(12)
            
            # --- ATTIVAZIONE RICERCA VIA JAVASCRIPT ---
            print("-> [STEP CERCA] Eseguo la ricerca tramite script JS...")
            try:
                await page.evaluate("""() => {
                    if(typeof sendPostRequest === 'function') {
                        sendPostRequest();
                    } else {
                        const btn = document.querySelector('button[onclick*="sendPostRequest"]');
                        if(btn) btn.click();
                    }
                }""")
                print("-> [STEP CERCA] Richiesta inviata con successo. Attendo aggiornamento...")
                await asyncio.sleep(16)
            except Exception as e:
                print(f"-> [ERRORE Cerca]: {e}")
            
            # --- 2. FILTRO CATEGORIA ---
            print(f"-> Clicco filtro categoria: {cat_id}")
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(14) 
            
            # --- 3. ESPANSIONE LISTA ---
            while True:
                btn_load_more = page.locator("button#btn-loadMore")
                if await btn_load_more.is_visible():
                    try:
                        await btn_load_more.click()
                        await page.wait_for_load_state("domcontentloaded", timeout=30000)
                        await asyncio.sleep(12)
                    except:
                        await asyncio.sleep(5)
                        break
                else:
                    break
            
            # --- 4. ESTRAZIONE ---
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            urls = list(set([await loc.get_attribute("href") for loc in locators]))
            print(f"-> Trovati {len(urls)} tornei. Estrazione...")
            
            for url in urls:
                full_torneo_url = f"https://www.fitp.it{url}"
                
                # Tentativo di apertura pagina torneo con retry
                torneo_aperto = False
                for t_pag in range(3):
                    try:
                        await page.goto(full_torneo_url, wait_until="domcontentloaded", timeout=60000)
                        torneo_aperto = True
                        break
                    except Exception as e:
                        print(f"    ! [Warning] Tentativo {t_pag+1} apertura torneo fallito: {e}")
                        await asyncio.sleep(5)
                
                if not torneo_aperto:
                    print(f"    ! [Errore] Impossibile caricare il torneo dopo 3 tentativi. Salto.")
                    continue
                
                try:
                    if await page.locator("text=non e' al momento disponibile").is_visible(): 
                        continue
                    
                    count = await page.locator("text=Dettaglio >").count()
                    for i in range(count):
                        # Ri-navighiamo alla pagina del torneo per sicurezza prima di cliccare ogni dettaglio
                        await page.goto(full_torneo_url, wait_until="domcontentloaded", timeout=60000)
                        btn = page.locator("text=Dettaglio >").nth(i)
                        
                        if await btn.is_visible():
                            # Clic sul dettaglio protetto da tentativi
                            cliccato = False
                            for t_click in range(3):
                                try:
                                    await btn.click(force=True)
                                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                                    await asyncio.sleep(4)
                                    cliccato = True
                                    break
                                except Exception as e:
                                    print(f"    ! [Warning] Tentativo {t_click+1} click Dettaglio fallito: {e}")
                                    await asyncio.sleep(3)
                            
                            if not cliccato:
                                continue
                            
                            categoria = await page.locator("h1.cc-title-main").first.text_content()
                            tabellone_el = page.locator("span#spn-tournament-description")
                            tabellone = await tabellone_el.text_content() if await tabellone_el.count() > 0 else "N/A"
                            giocatori = [await el.text_content() for el in await page.locator("a[href*='Pagina-Giocatore']").all()]
                            
                            dati_categoria["tornei"].append({
                                "torneo": url, 
                                "categoria": categoria.strip() if categoria else "", 
                                "tabellone": tabellone.strip(), 
                                "iscritti": [g.strip() for g in giocatori]
                            })
                            print(f"    -> Estratto: {tabellone.strip()}")
                except Exception as e:
                    print(f"    ! Errore su {url[-10:]}: {e}")
            
            # --- 5. SALVATAGGIO ---
            with open(filename, "w", encoding="utf-8") as f: 
                json.dump(dati_categoria, f, ensure_ascii=False, indent=4)
            print(f"-> SALVATO: {filename}")
            
        await browser.close()
        print("--- [END] Processo completato. ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
