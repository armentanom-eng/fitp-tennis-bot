import asyncio
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
STATUSES = ["In corso", "Iscrizioni aperte"]
OUTPUT_FILE = "Tornei_e_Iscritti.json"

async def estrai_iscritti_u14(page):
    """
    Gestisce l'interazione dinamica (senza cambiare URL).
    Clicca 'Dettaglio' sulla categoria corretta ed estrae i nomi.
    """
    print("    DEBUG: Cerco il blocco card con categoria 'Singolare Femminile Under 14'...", flush=True)
    
    try:
        # LOGICA: Trova il div che contiene la categoria E il link "Dettaglio"
        # Usiamo .first per assicurarci di prendere il primo blocco che corrisponde
        card = page.locator("div:has-text('Singolare Femminile Under 14')").filter(
            has=page.get_by_role("link", name="Dettaglio")
        ).first
        
        if await card.count() > 0:
            print("    DEBUG: Trovata card! Clicco sul link 'Dettaglio'...", flush=True)
            
            # Clicchiamo sul link "Dettaglio" all'interno della card
            await card.get_by_role("link", name="Dettaglio").click()
            
            # ATTESA: Attendiamo che appaia la lista iscritti (es. classe .cc-name)
            # Senza cambiare URL, la pagina inietta la lista via JS
            try:
                await page.wait_for_selector(".cc-name", timeout=10000)
                
                # Estrazione nomi
                nomi = await page.locator(".cc-name").all_text_contents()
                lista_pulita = [n.strip() for n in nomi if n.strip()]
                
                print(f"    DEBUG: Estratti {len(lista_pulita)} nomi.", flush=True)
                return lista_pulita
                
            except Exception as e:
                print(f"    DEBUG: I nomi non sono apparsi dopo il click. {e}", flush=True)
                return None
        else:
            print("    DEBUG: Categoria 'Singolare Femminile Under 14' non trovata in questa pagina.", flush=True)
            return None
            
    except Exception as e:
        print(f"    ! Errore critico in estrazione: {e}", flush=True)
        return None

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    dati_finali = {}
    
    async with async_playwright() as p:
        # headless=True è OBBLIGATORIO per GitHub Actions
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        start_date_filter = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        
        for status in STATUSES:
            print(f"\n--- Inizio sessione: Stato '{status}' ---", flush=True)
            page = await context.new_page()
            
            # Navigazione iniziale
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            await asyncio.sleep(3) 
            
            # Applicazione filtri
            await page.click('button[data-id="select_status"]')
            await asyncio.sleep(1)
            await page.get_by_role("listbox").get_by_role("option", name=status).click()
            
            await page.click('button[data-id="id_regioneSearch"]')
            await asyncio.sleep(1)
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            
            await page.click('button[data-id="id_provinciaSearch"]')
            await asyncio.sleep(1)
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            
            await page.fill("#dpk_start_date", start_date_filter)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(2)
            
            # Clicca Giovanili
            await page.locator('a[data-id="t_giovanili"]').first.click()
            await asyncio.sleep(3) 
            
            # Caricamento infinito
            while await page.locator("#btn-loadMore").is_visible():
                print("    Caricamento altri risultati...", flush=True)
                await page.click("#btn-loadMore")
                await asyncio.sleep(2)
            
            # Recupero link tornei
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            print(f"    Trovati {len(links)} tornei.", flush=True)
            
            # Ciclo tornei
            for link in links:
                full_url = f"https://www.fitp.it{link}"
                try:
                    # Carichiamo il torneo (URL cambia qui)
                    await page.goto(full_url, wait_until="domcontentloaded")
                    await asyncio.sleep(3)
                    
                    # Recupero titolo
                    title_el = page.locator("h1.cc-title-main")
                    nome_torneo = (await title_el.text_content()).strip() if await title_el.count() > 0 else "Torneo sconosciuto"
                    print(f"    -> Analizzo torneo: {nome_torneo} | Link: {full_url}", flush=True)
                    
                    # Estrazione (SPA, URL NON cambia)
                    iscritti = await estrai_iscritti_u14(page)
                    
                    if iscritti:
                        dati_finali[nome_torneo] = iscritti
                        print(f"       [OK] Trovati {len(iscritti)} iscritti.", flush=True)
                    
                except Exception as e: 
                    print(f"    !! Errore su {full_url}: {e}", flush=True)
            
            await page.close()
            
        # Salvataggio
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dati_finali, f, ensure_ascii=False, indent=4)
            print(f"\n--- [OK] File {OUTPUT_FILE} salvato con successo. ---", flush=True)
            
        await browser.close()
        print(f"--- Bot completato ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
