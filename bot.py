import asyncio
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright

# Configurazione
BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
CATEGORIES = {"t_giovanili": "Giovanili_Partite.json"}
ISCRITTI_FILE = "Iscritti_Giovanili.json"
# Filtri richiesti
STATUS_LIST = ["In corso", "Iscrizioni aperte"]

async def estrai_iscritti(page):
    try:
        # Attendiamo che la sezione partecipanti sia caricata
        if await page.locator(".cc-section-participants").count() > 0:
            nomi = await page.locator(".cc-name").all_text_contents()
            return [n.strip() for n in nomi if n.strip()]
    except Exception as e:
        print(f"    ! Errore estrazione iscritti: {e}", flush=True)
    return []

async def run_bot():
    print(f"--- Avvio Bot alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    iscritti_report = {"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        for cat_id in CATEGORIES:
            for status in STATUS_LIST:
                print(f"\n--- Filtro attivo: {status} ---", flush=True)
                await page.goto(BASE_URL, wait_until="networkidle")
                
                # 1. Selezione Categoria (Giovanili)
                await page.locator(f'a[data-id="{cat_id}"]').click()
                await asyncio.sleep(2)
                
                # 2. Selezione Stato (In corso / Iscrizioni aperte)
                await page.click('button[data-id="select_status"]')
                await page.get_by_role("listbox").get_by_role("option", name=status).click()
                await asyncio.sleep(2)
                # Invio per confermare filtri se necessario
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)

                # Caricamento elenco tornei
                while await page.locator("#btn-loadMore").is_visible():
                    await page.click("#btn-loadMore")
                    await asyncio.sleep(2)
                
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                urls_tornei = list(set([await loc.get_attribute("href") for loc in locators]))
                
                for url_torneo in urls_tornei:
                    full_url = f"https://www.fitp.it{url_torneo}"
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        
                        # --- NUOVA LOGICA DI RICERCA CATEGORIA (PIÙ ROBUSTA) ---
                        # Cerchiamo tutti i link "Dettaglio"
                        dettagli = page.get_by_role("link", name="Dettaglio")
                        trovato = False
                        
                        count = await dettagli.count()
                        for i in range(count):
                            link = dettagli.nth(i)
                            # Prendiamo il contenitore del blocco categoria
                            container = link.locator("xpath=ancestor::div[contains(@class, 'cc-single-tournament')]")
                            text_content = await container.text_content()
                            
                            # Controllo flessibile: devono esserci tutte le parole chiave
                            if all(k in text_content for k in ["Singolare", "Femminile", "Under 14"]):
                                print(f"    -> Trovata categoria: {text_content.strip()[:50]}...", flush=True)
                                await link.click()
                                await page.wait_for_load_state("networkidle")
                                
                                # Estrazione
                                lista = await estrai_iscritti(page)
                                if lista:
                                    iscritti_report["tornei"].append({
                                        "status": status,
                                        "torneo": text_content.strip(),
                                        "iscritti": lista
                                    })
                                    print(f"    [OK] Trovati {len(lista)} iscritti.")
                                else:
                                    print("    [!] Categoria trovata ma nessun iscritto (o errore caricamento).")
                                
                                trovato = True
                                break # Usciamo dal ciclo delle categorie
                        
                        if not trovato:
                            # Log opzionale per debug
                            pass

                    except Exception as e:
                        print(f"    !! Errore sul torneo {full_url}: {e}")

        # Salva i risultati
        with open(ISCRITTI_FILE, "w", encoding="utf-8") as f:
            json.dump(iscritti_report, f, ensure_ascii=False, indent=4)
            
        await browser.close()
        print("--- Bot completato ---")

if __name__ == "__main__":
    asyncio.run(run_bot())
