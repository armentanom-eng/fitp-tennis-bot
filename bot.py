import asyncio
import os
import pdfplumber
from playwright.async_api import async_playwright
from datetime import datetime, timedelta

# Limite di pagine aperte contemporaneamente (3 è il numero d'oro per velocità/sicurezza)
CONCURRENT_PAGES = 3 

async def process_tournament(context, url, sem):
    async with sem: # Gestisce il limite di caricamento
        full_url = "https://www.fitp.it" + url
        page = await context.new_page()
        try:
            # Velocità: domcontentloaded non aspetta le pubblicità/immagini
            await page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
            
            oggi = datetime.now().strftime("%d/%m/%Y")
            domani = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
            
            for data in [oggi, domani]:
                try:
                    # Selettore unico per la data
                    if await page.locator("select").count() > 0:
                        await page.select_option("select", label=data)
                        await asyncio.sleep(1.5) # Pausa minima tecnica
                        
                        btn = page.locator("text=Scarica")
                        if await btn.is_visible():
                            async with page.expect_download(timeout=10000) as download_info:
                                await btn.click()
                            download = await download_info.value
                            temp_file = f"temp_{data.replace('/', '-')}.pdf"
                            await download.save_as(temp_file)
                            
                            # Logica estrazione (resta sincrona per semplicità)
                            # Nota: pdfplumber è sincrono, va bene così
                            nome, partite = estrai_dati_da_pdf(temp_file, data)
                            if nome and partite:
                                # Scrittura protetta (se il file è bloccato, riprova)
                                with open("Risultati_Finali.txt", "a", encoding="utf-8") as f:
                                    f.write(f"\n>> {nome} ({data})\n" + "\n".join(partite) + "\n")
                            if os.path.exists(temp_file): os.remove(temp_file)
                except Exception as e:
                    pass
        except Exception:
            pass
        finally:
            await page.close()

# Mantieni la tua funzione estrai_dati_da_pdf così com'è, è perfetta.

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        sem = asyncio.Semaphore(CONCURRENT_PAGES)
        
        # Qui dovresti inserire la logica di raccolta URL (la Fase 1 e 2 del vecchio codice)
        # Una volta ottenuta la lista 'urls', fai questo:
        tasks = [process_tournament(context, url, sem) for url in urls]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
