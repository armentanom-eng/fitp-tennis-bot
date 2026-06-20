import asyncio
import os
import pdfplumber
from playwright.async_api import async_playwright
from datetime import datetime

# CONFIGURAZIONE TEST: Elabora solo il primo torneo trovato
CONCURRENT_PAGES = 1 

def estrai_dati_da_pdf(percorso_pdf):
    print(f"--- ANALISI PDF: {percorso_pdf} ---")
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            if not pdf.pages: return None, []
            testo = pdf.pages[0].extract_text()
            if not testo: return None, []
            
            linee = testo.split('\n')
            nome_circolo = linee[0].strip()
            partite_trovate = []
            
            # Debug: stampiamo il contenuto per vedere come legge
            print(f"DEBUG: Trovato circolo '{nome_circolo}'. Prime 5 righe: {linee[:5]}")
            
            for i in range(len(linee)):
                if "Inizio ore:" in linee[i]:
                    orario = linee[i].replace("Inizio ore:", "").strip()
                    try:
                        g1 = linee[i+2].strip()
                        g2 = linee[i+4].strip()
                        # Verifichiamo la validità
                        if "vs" not in g1.lower() and len(g1) > 4:
                             partite_trovate.append(f"{g1}; {g2}; {orario}")
                             print(f"DEBUG: Trovata partita: {g1} vs {g2}")
                    except: continue
            return nome_circolo, partite_trovate
    except Exception as e:
        print(f"ERRORE PDF: {e}")
        return None, []

async def get_tournament_urls(page, categoria_id):
    print(f"[{categoria_id}] Navigazione...", flush=True)
    await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
    
    await page.select_option("#select_status", label="In corso")
    await page.click(f'a[data-id="{categoria_id}"]')
    await page.wait_for_load_state("networkidle")
    
    print(f"[{categoria_id}] Applicazione filtro Lazio...", flush=True)
    # Selezione Regione
    await page.click('button[data-id="id_regioneSearch"]')
    await page.wait_for_selector('span.text:has-text("Lazio")', state="visible")
    await page.click('span.text:has-text("Lazio")')
    
    # ATTENZIONE: Questo wait è fondamentale per assicurarsi che la tabella si ricarichi
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(2) # Pausa di sicurezza per il ricaricamento asincrono
    
    # Prendi solo il PRIMO link (per il test)
    first_link = await page.locator("a[href*='Dettaglio-Competizione']").first.get_attribute("href")
    return [first_link] if first_link else []

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Mettiamo headless=False per vedere cosa fa
        context = await browser.new_context(accept_downloads=True)
        
        categorie = [("t_giovanili", "Test_Giovanili.txt"), ("t_affiliati", "Test_Open.txt")]
        
        for cat_id, file_name in categorie:
            print(f"\n>>> TEST CATEGORIA: {cat_id} <<<")
            p_scout = await context.new_page()
            urls = await get_tournament_urls(p_scout, cat_id)
            await p_scout.close()
            
            if urls:
                print(f"[{cat_id}] Trovato torneo: {urls[0]}")
                # Creiamo una pagina per il download
                page = await context.new_page()
                full_url = "https://www.fitp.it" + urls[0]
                await page.goto(full_url, wait_until="networkidle")
                
                # Semplifichiamo: proviamo a scaricare quello che è selezionato di default
                # Senza selezionare date, vediamo se c'è un bottone scarica subito
                btn = page.locator("text=Scarica")
                if await btn.is_visible():
                    async with page.expect_download() as download_info:
                        await btn.click()
                    download = await download_info.value
                    await download.save_as("test_file.pdf")
                    
                    nome, partite = estrai_dati_da_pdf("test_file.pdf")
                    if nome:
                        with open(file_name, "w", encoding="utf-8") as f:
                            f.write(f"TEST SUCCESS: {nome}\n" + "\n".join(partite))
                        print(f"!!! SCRITTURA AVVENUTA NEL FILE: {file_name}")
                
                await page.close()
            else:
                print(f"[{cat_id}] Nessun torneo trovato (il filtro potrebbe aver sbagliato).")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
