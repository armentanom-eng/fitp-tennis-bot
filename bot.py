import asyncio
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
OUTPUT_FILE = "Tornei_e_Iscritti.json"

async def estrai_iscritti_u14(page):
    """
    Funzione con log di avanzamento dettagliati per capire dove si blocca.
    """
    print(f"    [DEBUG] Inizio ricerca categoria...", flush=True)
    
    try:
        # Cerchiamo l'elemento (usa 'text' per trovare la scritta ovunque)
        categoria = page.locator("text=Singolare Femminile Under 14").first
        
        if await categoria.count() == 0:
            print(f"    [DEBUG] ERRORE: Testo 'Singolare Femminile Under 14' non trovato nella pagina.", flush=True)
            return None
            
        print(f"    [DEBUG] Categoria trovata. Tentativo di click...", flush=True)
        await categoria.click()
        
        # Dopo il click, non navighiamo, ma la pagina dovrebbe cambiare.
        # Dobbiamo attendere che compaia la lista (es. una tabella o un div che prima non c'era)
        # Sostituisci '.cc-name' con la classe che vedi nell'ispettore per i nomi
        print(f"    [DEBUG] Click effettuato. Attendo comparsa elenco iscritti...", flush=True)
        
        try:
            # Attendiamo 8 secondi che appaia un elemento che contiene i nomi (es. .cc-name)
            await page.wait_for_selector(".cc-name", timeout=8000)
            print(f"    [DEBUG] Elenco iscritti rilevato!", flush=True)
        except Exception:
            print(f"    [DEBUG] ERRORE: Timeout - I nomi non sono comparsi dopo il click.", flush=True)
            return None
        
        # Estrazione nomi
        nomi_elementi = page.locator(".cc-name")
        nomi = await nomi_elementi.all_text_contents()
        lista_pulita = [n.strip() for n in nomi if n.strip()]
        
        print(f"    [DEBUG] Estratti {len(lista_pulita)} nomi con successo.", flush=True)
        return lista_pulita
            
    except Exception as e:
        print(f"    [DEBUG] CRITICO: Errore durante l'estrazione: {e}", flush=True)
        return None

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    dati_finali = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Messo headless=False così vedi cosa fa!
        context = await browser.new_context()
        
        print(f"    [DEBUG] Navigo su {BASE_URL}...", flush=True)
        page = await context.new_page()
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(5) # Attesa manuale per caricamento iniziale
        
        # (Qui dovresti inserire i filtri di selezione, ho messo una pausa per sicurezza)
        print(f"    [DEBUG] Filtri applicati (supposti). Recupero link tornei...", flush=True)
        
        # Recupero link tornei
        locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
        links = list(set([await loc.get_attribute("href") for loc in locators]))
        print(f"    [DEBUG] Trovati {len(links)} tornei da analizzare.", flush=True)
        
        for link in links:
            full_url = f"https://www.fitp.it{link}"
            print(f"\n    [DEBUG] --- ANALISI TORNEO: {full_url} ---", flush=True)
            try:
                await page.goto(full_url, wait_until="domcontentloaded")
                await asyncio.sleep(3) # Pausa per caricamento SPA
                
                # Eseguiamo l'estrazione
                iscritti = await estrai_iscritti_u14(page)
                
                if iscritti:
                    dati_finali[full_url] = iscritti
                    print(f"    [DEBUG] [OK] Salvati {len(iscritti)} iscritti.", flush=True)
                else:
                    print(f"    [DEBUG] [FAIL] Nessun iscritto estratto per questo torneo.", flush=True)
                
            except Exception as e: 
                print(f"    [DEBUG] [CRITICO] Errore sulla pagina {full_url}: {e}", flush=True)
        
        # Salvataggio
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dati_finali, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print(f"--- Bot completato ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
