import asyncio
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
OUTPUT_FILE = "Tornei_e_Iscritti.json"

async def estrai_iscritti_u14(page):
    """
    Strategia per SPA: Clicca sull'elemento dinamico e attende 
    la comparsa dei risultati (i nomi) senza navigare.
    """
    try:
        # Attendiamo un secondo per assicurarci che la pagina sia reattiva
        await asyncio.sleep(1)
        
        print("    DEBUG: Cerco la categoria (anche con testo aggiuntivo)...", flush=True)
        
        # 'get_by_text' con exact=False trova l'elemento anche se contiene altro testo
        categoria_locator = page.get_by_text("Singolare Femminile Under 14", exact=False).first
        
        if await categoria_locator.count() > 0:
            print("    DEBUG: Categoria trovata. Clicco e attendo i nomi...", flush=True)
            await categoria_locator.click()
            
            # Attendiamo che appaiano i nomi degli iscritti (timeout 5s)
            # Se la classe non è .cc-name, cambiala con quella corretta che vedi nell'ispettore
            try:
                await page.wait_for_selector(".cc-name", state="visible", timeout=5000)
                
                # Estrazione nomi
                nomi_elementi = page.locator(".cc-name")
                nomi = await nomi_elementi.all_text_contents()
                lista_pulita = [n.strip() for n in nomi if n.strip()]
                
                print(f"    DEBUG: Estratti {len(lista_pulita)} nomi.", flush=True)
                return lista_pulita
            except Exception:
                print("    DEBUG: I nomi non sono comparsi dopo il click.", flush=True)
                return None
        else:
            print("    DEBUG: Testo 'Singolare Femminile Under 14' non trovato.", flush=True)
            return None
            
    except Exception as e:
        print(f"    ! Errore in estrazione: {e}", flush=True)
        return None

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    dati_finali = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        # Navigazione iniziale per ottenere i link dei tornei
        page = await context.new_page()
        await page.goto(BASE_URL, wait_until="networkidle")
        
        # (Qui inserisci la logica di filtro che avevi già, ho omesso per brevità)
        # ... (Filtri Stato/Regione/Provincia) ...
        
        # Recupero link tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        links = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"    Trovati {len(links)} tornei.", flush=True)
        
        # Ciclo principale
        for link in links:
            full_url = f"https://www.fitp.it{link}"
            try:
                # Ogni volta carichiamo una pagina diversa, quindi ripartiamo da zero
                await page.goto(full_url, wait_until="networkidle")
                
                # Recupero titolo
                nome_torneo = await page.locator("h1.cc-title-main").text_content() or "Torneo"
                print(f"    -> Analizzo: {nome_torneo.strip()}", flush=True)
                
                # Eseguiamo l'estrazione dinamica
                iscritti = await estrai_iscritti_u14(page)
                if iscritti:
                    dati_finali[nome_torneo.strip()] = iscritti
                    print(f"       [OK] Trovati {len(iscritti)} iscritti.", flush=True)
                
            except Exception as e: 
                print(f"    !! Errore su {full_url}: {e}", flush=True)
        
        # Salvataggio
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dati_finali, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print(f"--- Bot completato ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
