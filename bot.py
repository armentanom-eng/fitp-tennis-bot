import asyncio
import json
import os
from playwright.async_api import async_playwright

# --- CONFIGURAZIONE ---
# Inserisci qui l'URL esatto della pagina FITP che contiene la lista iscritti
URL_TARGET = "https://www.fitp.it/Tornei/..." 
FILE_OUTPUT = "iscritti_torneo.json"

async def main():
    print(f"[LOG] Avvio script per il sito FITP...", flush=True)
    
    async with async_playwright() as p:
        print(f"[LOG] Avvio browser...", flush=True)
        browser = await p.chromium.launch(headless=True)
        
        # Uso un user-agent reale per non essere bloccati dal sito
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"[LOG] Navigazione verso: {URL_TARGET}", flush=True)
            # Caricamento pagina
            await page.goto(URL_TARGET, wait_until="networkidle")
            
            print(f"[LOG] Pagina caricata. Cerco la sezione iscritti...", flush=True)
            
            # Controllo se il contenitore degli iscritti esiste
            # Il selettore è basato sulla struttura standard FITP
            container = page.locator(".cc-section-participants")
            
            if await container.is_visible(timeout=10000):
                print(f"[LOG] Sezione iscritti trovata. Eseguo scroll per caricamento dinamico...", flush=True)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                # Estrazione nomi
                print(f"[LOG] Estrazione lista nomi...", flush=True)
                nomi_elements = page.locator(".cc-name")
                nomi_testo = await nomi_elements.all_text_contents()
                
                lista_iscritti = list(set([n.strip() for n in nomi_testo if n.strip()]))
                
                print(f"[LOG] Trovati {len(lista_iscritti)} iscritti.", flush=True)
                
                # Salvataggio file
                dati = {
                    "data_estrazione": "2026-06-21",
                    "url_origine": URL_TARGET,
                    "numero_iscritti": len(lista_iscritti),
                    "iscritti": lista_iscritti
                }
                
                with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
                    json.dump(dati, f, ensure_ascii=False, indent=4)
                
                print(f"[LOG] Dati salvati correttamente nel file: {FILE_OUTPUT}", flush=True)
                
            else:
                print(f"[ERRORE] Sezione iscritti (.cc-section-participants) non trovata.", flush=True)
                print(f"[DEBUG] Il selettore CSS potrebbe essere cambiato o sei sulla pagina sbagliata.", flush=True)
                
        except Exception as e:
            print(f"[ERRORE] Si è verificato un errore: {e}", flush=True)
            
        finally:
            print(f"[LOG] Chiusura browser.", flush=True)
            await browser.close()

if __name__ == "__main__":
    if "https://www.fitp.it" in URL_TARGET:
        asyncio.run(main())
    else:
        print("[ERRORE] URL non valido. Inserisci un link che inizia con https://www.fitp.it")
