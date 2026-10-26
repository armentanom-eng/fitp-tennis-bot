import asyncio
import pdfplumber
import re
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "https://www.fitp.it/Tornei/Ricerca-tornei"
FILE_REGISTRO = "notifiche_inviate.json"

CATEGORIES = {
    "t_giovanili": "Iscrizioni_Aperte_Giovanili_pdf.json", 
    "t_affiliati": "Iscrizioni_Aperte_Open_pdf.json"
}

def carica_registro():
    if os.path.exists(FILE_REGISTRO):
        try:
            with open(FILE_REGISTRO, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def salva_registro(registro):
    with open(FILE_REGISTRO, "w", encoding="utf-8") as f:
        json.dump(registro, f, indent=4, ensure_ascii=False)

def invia_notifiche_giocatore(riga_partita, nome_torneo, data_target):
    mittente = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    destinatari = ["armentano.m@gmail.com", "Marcella.dellanna@gmail.com"]
    
    if not mittente or not password:
        print("-> [Email] Credenziali non configurate nei Secrets di GitHub.")
        return

    # ID univoco per evitare invii multipli della stessa partita
    id_univoco = f"{nome_torneo}_{data_target}_{riga_partita}".replace(" ", "_")
    registro = carica_registro()
    
    if id_univoco in registro:
        print(f"-> [Email] Notifica già inviata in precedenza per questa partita.")
        return

    oggetto = "tornei fit"
    testo = f"Il giocatore Armentano è stato trovato nel torneo '{nome_torneo}' in data {data_target}.\nDettagli: {riga_partita}"

    invio_riuscito = True
    for destinatario in destinatari:
        msg = MIMEMultipart()
        msg['From'] = mittente
        msg['To'] = destinatario
        msg['Subject'] = oggetto
        msg.attach(MIMEText(testo, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(mittente, password)
            server.sendmail(mittente, destinatario, msg.as_string())
            server.quit()
            print(f"-> [Email] Inviata con successo a {destinatario}!")
        except Exception as e:
            print(f"-> [Email Errore] Impossibile inviare a {destinatario}: {e}")
            invio_riuscito = False

    if invio_riuscito:
        registro.append(id_univoco)
        salva_registro(registro)

def get_pdf_info(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        row_text = " ".join([str(cell).strip() for cell in row if cell and str(cell).strip()])
                        if len(row_text) > 5: matches.append(row_text)
    except: pass
    return matches

def format_line_for_swift(raw_text, date_target):
    clean_text = raw_text.replace('\n', ' ').strip()
    return f"{date_target}; {clean_text}"

async def run_bot():
    print("--- [START] Avvio estrazione completa e resistente (Iscrizioni aperte) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n>>> Processo categoria: {cat_id}")
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            await page.goto(BASE_URL, timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            print("-> Seleziono Stato: Iscrizioni aperte...")
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name="Iscrizioni aperte").click()
            await asyncio.sleep(2)
            
            print("-> Seleziono Regione: Lazio...")
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(2) 
            
            print("-> Seleziono Provincia: Roma...")
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(2)
            
            oggi = datetime.now()
            data_inizio = (oggi - timedelta(days=30)).strftime("%d/%m/%Y")
            
            print(f"-> [STEP DATA] Imposto Data Inizio: {data_inizio} | Data Fine: [VUOTA]")
            
            await page.evaluate(f"""() => {{
                const start = document.querySelector('#dpk_start_date');
                const end = document.querySelector('#dpk_end_date');
                
                if(start) {{
                    start.removeAttribute('min');
                    start.removeAttribute('max');
                    start.value = "{data_inizio}";
                    if (window.jQuery && jQuery(start).data('datepicker')) {{
                        jQuery(start).datepicker('setStartDate', null);
                        jQuery(start).datepicker('setDate', '{data_inizio}');
                    }}
                    start.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    start.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                
                if(end) {{
                    end.removeAttribute('min');
                    end.removeAttribute('max');
                    end.value = ""; 
                    if (window.jQuery && jQuery(end).data('datepicker')) {{
                        jQuery(end).datepicker('setDate', null);
                    }}
                    end.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    end.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""")
            await asyncio.sleep(2)
            
            print("-> [STEP CERCA] Eseguo la ricerca tramite script JS...")
            try:
                await page.evaluate("""() => {
                    if(typeof sendPostRequest === 'function') {
                        sendPostRequest();
                    } else {
                        const btn = document.querySelector('button[onclick*="sendPostRequest"]');
                        if(btn) btn.click();
                    }
                }""")
                print("-> [STEP CERCA] Richiesta inviata con successo. Attendo aggiornamento...")
                await asyncio.sleep(6)
            except Exception as e:
                print(f"-> [ERRORE Cerca]: {e}")
            
            print(f"-> Clicco sulla scheda categoria: {cat_id}")
            await page.wait_for_selector(f'a[data-id="{cat_id}"]')
            await page.locator(f'a[data-id="{cat_id}"]').first.click()
            await asyncio.sleep(6) 
            
            print("-> Espansione lista tornei...")
            while True:
                more_btn = page.locator("#btn-loadMore")
                if await more_btn.is_visible():
                    await more_btn.click()
                    await asyncio.sleep(6)
                else:
                    break
            
            links = list(set([await loc.get_attribute("href") for loc in await page.locator("a[href*='Dettaglio-Competizione']").all()]))
            print(f"   [Tornei trovati]: {len(links)}")
            
            for index, link in enumerate(links, start=1):
                try:
                    full_url = f"https://www.fitp.it{link}"
                    print(f"\n   --- Analizzo torneo {index}/{len(links)} ---")
                    await page.goto(full_url, timeout=60000)
                    await page.wait_for_load_state("networkidle")
                    
                    try:
                        nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                    except:
                        nome_torneo = "Torneo senza nome"
                    
                    print(f"   [Torneo]: {nome_torneo.strip()}")
                    
                    dropdown_selector = "#select-ordergame"
                    download_btn = page.locator("#btnOrderGameDownload")
                    
                    partite_totali = []
                    if await page.locator(dropdown_selector).is_visible():
                        oggi_ciclo = datetime.now()
                        for i in range(0, 2): 
                            data_target = (oggi_ciclo + timedelta(days=i)).strftime("%d/%m/%Y")
                            
                            if await page.locator(f"{dropdown_selector} option:has-text('{data_target}')").count() > 0:
                                await page.select_option(dropdown_selector, label=data_target)
                                await asyncio.sleep(5)
                                
                                if await download_btn.is_visible():
                                    async xd = page.expect_download(timeout=30000) # syntax fallback check
                                    async with page.expect_download(timeout=30000) as dl_info: 
                                        await download_btn.click()
                                    download = await dl_info.value
                                    path = await download.path()
                                    matches = get_pdf_info(path)
                                    for m in matches:
                                        formatted_line = format_line_for_swift(m, data_target)
                                        partite_totali.append(formatted_line)
                                        
                                        # Controllo se il cognome "armentano" è presente nella riga (case-insensitive)
                                        if "armentano" in formatted_line.lower():
                                            print(f"-> Trovato match per Armentano! Invio notifiche email...")
                                            invia_notifiche_giocatore(formatted_line, nome_torneo.strip(), data_target)
                    
                    if partite_totali:
                        json_data["tornei"].append({
                            "url": full_url, 
                            "nomeTorneo": nome_torneo.strip(), 
                            "data": datetime.now().strftime("%d/%m/%Y"), 
                            "partite": list(set(partite_totali))
                        })
                except Exception as e:
                    print(f"   [Errore su torneo]: {e}. Salto al prossimo.")
                    continue 
            
            with open(filename, "w", encoding="utf-8") as f: 
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            print(f"-> File {filename} salvato correttamente.")
            await page.close()
        
        await browser.close()
    print("--- [END] Processo completato correttamente ---")

if __name__ == "__main__": 
    asyncio.run(run_bot())
