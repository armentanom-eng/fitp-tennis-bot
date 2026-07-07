import asyncio
import json
from playwright.async_api import async_playwright

async def run_bot():
    print("--- [START] Avvio bot completo (4 file) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        # Navigazione e Filtri (Lazio, Roma, In Programma)
        await page.goto("https://www.fitp.it/Tornei/Ricerca-tornei", wait_until="networkidle")
        await page.click('button[data-id="select_status"]')
        await page.get_by_role("listbox").get_by_role("option", name="In programma").click()
        await page.click('button[data-id="id_regioneSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
        await asyncio.sleep(2)
        await page.click('button[data-id="id_provinciaSearch"]')
        await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)
        
        while await page.locator("button#btn-loadMore").is_visible():
            await page.click("button#btn-loadMore")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
        
        urls = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
        
        # Strutture dati separate
        dati_iscritti_giov = {"tornei": []}
        dati_iscritti_open = {"tornei": []}
        dati_partite_giov = {"tornei": []}
        dati_partite_open = {"tornei": []}
        
        for url in urls:
            await page.goto(f"https://www.fitp.it{url}", wait_until="networkidle")
            
            # Seleziona ultima data
            select = page.locator("select#select-ordergame")
            if await select.is_visible():
                await select.select_option(index=-1)
                await page.wait_for_load_state("networkidle")
            
            dettagli_btn = page.locator("span:has-text('Dettaglio >')")
            for i in range(await dettagli_btn.count()):
                try:
                    btn = page.locator("span:has-text('Dettaglio >')").nth(i)
                    await btn.click(force=True)
                    await page.wait_for_load_state("networkidle")
                    
                    categoria = await page.locator("h1.cc-title-main").first.text_content()
                    
                    # Estrazione Iscritti (Nomi a video)
                    nomi = await page.locator("div.cc-single-tournament span.cc-title").all_text_contents()
                    # Estrazione link Partite (PDF)
                    link_pdf = await page.locator("a#btnOrderGameDownload").get_attribute("href")
                    
                    entry_isc = {"torneo": url, "categoria": categoria.strip(), "iscritti": [n.strip() for n in nomi if n.strip()]}
                    entry_part = {"torneo": url, "categoria": categoria.strip(), "partita_pdf": link_pdf}
                    
                    if any(x in categoria for x in ["Under", "Giovanile", "U10", "U11", "U12", "U14", "U16"]):
                        dati_iscritti_giov["tornei"].append(entry_isc)
                        dati_partite_giov["tornei"].append(entry_part)
                    else:
                        dati_iscritti_open["tornei"].append(entry_isc)
                        dati_partite_open["tornei"].append(entry_part)
                    
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
                except:
                    await page.goto(f"https://www.fitp.it{url}")
        
        # SALVATAGGIO 4 FILE DISTINTI
        with open("Iscritti_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_iscritti_giov, f, ensure_ascii=False, indent=4)
        with open("Iscritti_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_iscritti_open, f, ensure_ascii=False, indent=4)
        with open("Partite_Giovanili_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_partite_giov, f, ensure_ascii=False, indent=4)
        with open("Partite_Open_In_Programma.json", "w", encoding="utf-8") as f:
            json.dump(dati_partite_open, f, ensure_ascii=False, indent=4)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
