import asyncio
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Mappa delle categorie con i nuovi nomi file richiesti
CATEGORIES = {
    "t_giovanili": "Iscritti_Giovanili_Aperte.json", 
    "t_affiliati": "Iscritti_Open_Aperte.json"
}

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"

async def run_bot():
    print("--- [START] Avvio estrazione WEB (Filtro: 'Iscrizioni aperte' - Resiliente) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.set_default_timeout(60000)
        
        # Iteriamo sulle categorie
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Elaborazione categoria: {cat_id}")
            dati_categoria = {"tornei": []}
            
            # Apertura con tentativi per la pagina principale
            successo_home = False
            for tentativo in range(3):
                try:
                    print(f"-> Apro la pagina (Tentativo {tentativo+1}/3): {BASE_URL}")
                    await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    successo_home = True
                    break
                except Exception as e:
                    print(f"-> [TIMEOUT HOME] Tentativo fallito: {e}. Riprovo tra 10 sec...")
                    await asyncio.sleep(10)
            
            if not successo_home:
                print(f"-> [ERRORE CRITICO] Impossibile caricare la home dei tornei. Salto categoria {cat_id}.")
                continue
            
            # --- 1. FILTRI BASE ---
            try:
                print("-> Seleziono Stato: Iscrizioni aperte...")
                await page.click('button[data-id="select_status"]', timeout=15000)
                await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click(timeout=15000)
                await asyncio.sleep(12)
                
                print("-> Seleziono Regione: Lazio...")
                await page.click('button[data-id="id_regioneSearch"]', timeout=15000)
                await page.get_by_role("listbox").get_by_role("option", name="Lazio").click(timeout=15000)
                await asyncio.sleep(12)
                
                print("-> Seleziono Provincia: Roma...")
                await page.click('button[data-id="id_provinciaSearch"]', timeout=15000)
                await page.get_by_role("listbox").get_by_role("option", name="Roma").click(timeout=15000)
                await asyncio.sleep(12)
            except Exception as e:
                print(f"-> [ERRORE FILTRI]: {e}")
            
            # --- IMPOSTAZIONE DATA INIZIO E SVUOTAMENTO DATA FINE ---
            oggi = datetime.now()
            data_inizio = (oggi - timedelta(days=30)).strftime("%d/%m/%Y")
            
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
            try:
                await page.locator(f'a[data-id="{cat_id}"]').first.click(timeout=15000)
                await page.wait_for_selector("a[href*='Dettaglio-Competizione']", timeout=25000)
            except Exception as e:
                print(f"-> [ERRORE Categoria {cat_id}]: {e}")
            await asyncio.sleep(14) 
            
            # --- 3. ESPANSIONE LISTA ---
            load_count = 0
            while load_count < 25:
                try:
                    btn_load_more = page.locator("button#btn-loadMore")
                    if await btn_load_more.is_visible():
                        load_count += 1
                        print(f"-> Clicco 'Carica altri' (Tentativo {load_count})...")
                        await btn_load_more.click()
                        await page.wait_for_load_state("domcontentloaded", timeout=30000)
                        await asyncio.sleep(12)
                    else:
                        break
                except:
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
                        # Torniamo alla pagina del torneo per ogni bottone con retry
                        torneo_ricaricato = False
                        for t_ric in range(3):
                            try:
                                await page.goto(full_torneo_url, wait_until="domcontentloaded", timeout=60
