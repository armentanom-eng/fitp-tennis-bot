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

    id_univoco = f"{nome_torneo}_{data_target}_{riga_partita}".replace(" ", "_")
    registro = carica_registro()
    
    if id_univoco in registro:
        print("-> [Email] Notifica già inviata in precedenza per questa partita.")
        return

    oggetto = "tornei fit"
    
    testo = f"""È stata trovata una partita per il giocatore Armentano!

📅 Data: {data_target}
🏆 Torneo: {nome_torneo}
⏰ Orario e Dettagli: {riga_partita}
"""

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
                        nome_torneo = await page.locator("h1").first.inner_text()
                        nome_torneo = nome_torneo.strip() if nome_torneo else "Torneo FITP"
                    except:
                        nome_torneo = "Torneo FITP"

                    pdf_links = await page.locator("a[href$='.pdf']").all()
                    for pdf_link in pdf_links:
                        href_pdf = await pdf_link.get_attribute("href")
                        if href_pdf:
                            if not href_pdf.startswith("http"):
                                href_pdf = f"https://www.fitp.it{href_pdf}"
                            
                            async with page.expect_download() as download_info:
                                await pdf_link.click()
                            download = await download_info.value
                            path_pdf = await download.path()
                            
                            righe_pdf = get_pdf_info(path_pdf)
                            for riga in righe_pdf:
                                if "armentano" in riga.lower():
                                    print(f"Trovato Armentano in {nome_torneo}: {riga}")
                                    invia_notifiche_giocatore(riga, nome_torneo, datetime.now().strftime("%d/%m/%Y"))
                except Exception as e:
                    print(f"-> [Errore Torneo {index}]: {e}")

if __name__ == "__main__":
    asyncio.run(run_bot())
