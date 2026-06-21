import asyncio
import json
from playwright.async_api import async_playwright

# --- CONFIGURA QUI ---
URL_DA_ESTRARRE = "INSERISCI_QUI_L_URL_DEL_TORNEO"
FILE_OUTPUT = "iscritti_estrazione.json"

async def estrai_iscritti():
    print(f"[LOG] Avvio script...", flush=True)
    
    async with async_playwright() as p:
        print(f"[LOG] Avvio browser...", flush=True)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print(f"[LOG] Navigazione su: {URL_DA_ESTRARRE}", flush=True)
            await page.goto(URL_DA_ESTRARRE, wait_until="networkidle")
            
            print(f"[LOG] Controllo se la sezione iscritti è presente...", flush=True)
            # Attende fino a 15 secondi la sezione iscritti
            if await page.locator(".cc-section-participants").is_visible(timeout=15000):
                print(f"[LOG] Sezione trovata. Eseguo scroll per caricare tutti i dati...", flush=True)
                
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3) # Pausa per caricamento
                
                print(f"[LOG] Estrazione nomi in corso...", flush=True)
                nomi = await page.locator(".cc-name").all_text_contents()
                lista_iscritti = list(set([n.strip() for n in nomi if n.strip()]))
                
                print(f"[LOG] Trovati {len(lista_iscritti)} iscritti.", flush=True)
                
                data = {
                    "url": URL_DA_ESTRARRE,
                    "totale": len(lista_iscritti),
                    "iscritti": lista_iscritti
                }
                
                print(f"[LOG] Salvataggio su {FILE_OUTPUT}...", flush=True)
                with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                print(f"[LOG] Operazione completata con successo.", flush=True)
            
            else:
                print(f"[ERRORE] Timeout o sezione .cc-section-participants non trovata.", flush=True)
                print(f"[DEBUG] Verifica se l'URL è corretto o se la pagina è cambiata.", flush=True)
                
        except Exception as e:
            print(f"[ERRORE] Si è verificato un errore critico: {e}", flush=True)
        finally:
            print(f"[LOG] Chiusura browser.", flush=True)
            await browser.close()

if __name__ == "__main__":
    if URL_DA_ESTRARRE != "INSERISCI_QUI_L_URL_DEL_TORNEO":
        asyncio.run(estrai_iscritti())
    else:
        print("[ATTENZIONE] Devi inserire un URL valido nella variabile URL_DA_ESTRARRE alla riga 6.")
