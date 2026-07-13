import asyncio
from playwright.async_api import async_playwright

async def run_bot():
    async with async_playwright() as p:
        # 1. Impostiamo una risoluzione desktop standard per evitare che elementi finiscano fuori viewport
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        try:
            # Sostituisci con l'URL corretto
            await page.goto("URL_DEL_SITO_FITP", wait_until="networkidle")

            # 2. Definiamo il locator
            opt = page.locator("a:has-text('Lazio')").first

            # 3. Approccio "Resiliente":
            # - Aspettiamo che l'elemento sia presente nel DOM
            # - Scorriamo la pagina verso l'elemento
            # - Verifichiamo che sia visibile
            # - Clicchiamo
            await opt.wait_for(state="attached", timeout=30000)
            await opt.scroll_into_view_if_needed()
            
            # Verifichiamo la visibilità prima di cliccare
            if await opt.is_visible():
                await opt.click(timeout=10000)
            else:
                print("L'elemento non è visibile, controllo overlay...")
                # Se non è visibile, a volte serve cliccare un bottone di menu prima
                # es: await page.click("button.menu-toggler")
                await opt.click(force=True)

            print("Click eseguito con successo!")

        except Exception as e:
            print(f"Errore durante l'esecuzione: {e}")
            # Opzionale: salva uno screenshot per capire cosa vedeva il bot al momento dell'errore
            await page.screenshot(path="debug_error.png")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
