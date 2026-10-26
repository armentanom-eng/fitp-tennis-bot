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

# Nomi dei file di output per i tornei In Programma
CATEGORIES = {
    "t_giovanili": "Iscritti_Giovanili_In_Programma.json", 
    "t_affiliati": "Iscritti_Open_In_Programma.json"
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

def invia_notifiche_giocatore(riga_formattata, nome_torneo, data_target):
    mittente = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    destinatari = ["armentano.m@gmail.com", "Marcella.dellanna@gmail.com"]
    
    if not mittente or not password:
        print("-> [Email] Credenziali non configurate nei Secrets di GitHub.")
        return

    # ID univoco per evitare invii multipli della stessa partita
    id_univoco = f"{nome_torneo}_{data_target}_{riga_formattata}".replace(" ", "_")
    registro = carica_registro()
    
    if id_univoco in registro:
        print("-> [Email] Notifica già inviata in precedenza per questa partita.")
        return

    oggetto = "tornei fit"
    testo = f"""È stata trovata una partita per il giocatore (Armentano / Dalia / Marie)!

📅 Data: {data_target}
🏆 Torneo: {nome_torneo}
⏰ Dettagli: {riga_formattata}
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

def format_line_for_swift(raw_text, date_target):
    text = raw_text.replace("\n", " ").strip()
    match_time = re.search(r"(\d{2})[:.](\d{2})", text)
    time = f"{match_time.group(1)}:{match_time.group(2)}" if match_time else "00:00"
    text = re.sub(r"(INIZIO|ORE|NON PRIMA DI|TABELLONE)?[:\s]*\d{2}[:.](\d{2})", "", text, flags=re.IGNORECASE)
    
    partite = re.findall(r"([A-Z\s\d\(\)àèìòùÀÈÌÒÙ]+?)\s+vs\s+([A-Z\s\d\(\)àèìòùÀÈÌÒÙ]+)", text, flags=re.IGNORECASE)
    if partite:
        clean = [f"{p[0].strip()} vs {p[1].strip()}" for p in partite]
        return f"{date_target}; {time}; {'; '.join(clean)}"
    return f"{date_target}; {time}; {text.strip()}"

def get_pdf_info(pdf_path):
    matches = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        row_text = " ".join([str(cell).strip() for cell in row if cell])
                        if len(row_text) > 5: matches.append(row_text)
    except: pass
    return matches

async def run_bot():
    print("--- [DEBUG DATE V8] Avvio script bot (In Programma) ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items():
            print(f"\n========================================")
            print(f">> [CATEGORY START] Processo categoria: {cat_id}")
            print(f"========================================")
            
            json_data = {"report_data": datetime.now().strftime("%d/%m/%Y %H:%M"), "tornei": []}
            page = await context.new_page()
            
            print(f"-> Apro la pagina: {BASE_URL}")
            await page.goto(BASE_URL, timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            # --- 1. APPLICAZIONE FILTRI A TENDINA ---
            print("-> [Filtro 1/3] Seleziono Stato: In programma...")
            await page.click('button[data-id="select_status"]')
            await page.get_by_role("listbox").get_by_role("option", name=re.compile("in programma", re.IGNORECASE)).click()
            await asyncio.sleep(2)
            
            print("-> [Filtro 2/3] Seleziono Regione: Lazio...")
            await page.click('button[data-id="id_regioneSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Lazio").click()
            await asyncio.sleep(2)
            
            print("-> [Filtro 3/3] Seleziono Provincia: Roma...")
            await page.click('button[data-id="id_provinciaSearch"]')
            await page.get_by_role("listbox").get_by_role("option", name="Roma").click()
            await asyncio.sleep(2)
            
            # --- 2. IMPOSTAZIONE DATA INIZIO E SVUOTAMENTO DATA FINE ---
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
            
            # --- 3. ATTIVAZIONE RICERCA VIA JAVASCRIPT ---
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

            # --- 4. SELEZIONE CATEGORIA ---
            print(f"-> Clicco sulla scheda categoria: {cat_id}")
            cat_selector = f'a[data-id="{cat_id}"]'
            try:
                await page.wait_for_selector(cat_selector, timeout=30000)
                await page.locator(cat_selector).first.click()
                print("-> Categoria selezionata con successo.")
            except Exception as e:
                print(f"-> [ERRORE Categoria {cat_id}]: {e}")
            
            await asyncio.sleep(6)
            
            # --- 5. ESPANSIONE LISTA ---
            print("-> Controllo presenza pulsante 'Carica altri' (#btn-loadMore)...")
            load_count = 0
            while True:
                btn_load_more = page.locator("#btn-loadMore")
                if await btn_load_more.is_visible():
                    load_count += 1
                    print(f"-> Clicco 'Carica altri' (Tentativo {load_count})...")
                    await btn_load_more.click()
                    await asyncio.sleep(6)
                else:
                    print("-> Nessun altro 'Carica altri' disponibile.")
                    break
            
            locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
            links = list(set([await loc.get_attribute("href") for loc in locators]))
            print(f"-> [RISULTATO FINALE] Tornei trovati per {cat_id}: {len(links)}")
            
            for index, link in enumerate(links, start=1):
                full_url = f"https://www.fitp.it{link}"
                print(f"\n   --- Analizzo torneo {index}/{len(links)} ---")
                await page.goto(full_url, timeout=60000)
                
                try:
                    nome_torneo = await page.locator("h1.cc-title-main.spn-competition-description").inner_text()
                except:
                    nome_torneo = "Torneo senza nome"
                
                print(f"   [Torneo]: {nome_torneo.strip()}")
                
                dropdown_selector = "#select-ordergame"
                download_btn = page.locator("#btnOrderGameDownload")
                
                if await page.locator(dropdown_selector).is_visible():
                    oggi_ciclo = datetime.now()
                    for i in range(0, 2):  # Oggi e Domani per i PDF
                        data_target = (oggi_ciclo + timedelta(days=i)).strftime("%d/%m/%Y")
                        
                        if await page.locator(f"{dropdown_selector} option:has-text('{data_target}')").count() > 0:
                            print(f"      -> Seleziono data {data_target} dal menu tendina...")
                            await page.select_option(dropdown_selector, label=data_target)
                            await asyncio.sleep(5)
                            
                            if await download_btn.is_visible():
                                print(f"      -> Scarico PDF per il {data_target}...")
                                async with page.expect_download() as dl_info: 
                                    await download_btn.click()
                                download = await dl_info.value
                                await download.save_as("temp.pdf")
                                matches = get_pdf_info("temp.pdf")
                                print(f"      -> Trovate {len(matches)} righe nel PDF.")
                                
                                formatted_matches = []
                                for m in matches:
                                    fmt_line = format_line_for_swift(m, data_target)
                                    formatted_matches.append(fmt_line)
                                    
                                    # Controllo presenza di almeno una delle parole chiave (case-insensitive)
                                    parole_chiave = ["armentano", "dalia", "marie"]
                                    if any(chiave in m.lower() for chiave in parole_chiave):
                                        print(f"Trovato match in {nome_torneo}: {m}")
                                        invia_notifiche_giocatore(fmt_line, nome_torneo.strip(), data_target)
                                
                                if formatted_matches:
                                    json_data["tornei"].append({
                                        "nome": nome_torneo.strip(),
                                        "data": data_target,
                                        "partite": formatted_matches
                                    })
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            print(f"-> Dati salvati con successo su {filename}")

if __name__ == "__main__":
    asyncio.run(run_bot())
