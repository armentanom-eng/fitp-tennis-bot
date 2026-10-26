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

# Nomi dei file di output
CATEGORIES = {
    "t_giovanili": "Giovanili_Partite_incorsopdf.json", 
    "t_affiliati": "Open_Partite_incorsopdf.json"
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
    print("-> [DEBUG EMAIL] Avvio funzione invia_notifiche_giocatore...")
    mittente = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    destinatari = ["armentano.m@gmail.com", "Marcella.dellanna@gmail.com"]
    
    print(f"-> [DEBUG EMAIL] EMAIL_USER presente: {bool(mittente)} (Valore: {mittente})")
    print(f"-> [DEBUG EMAIL] EMAIL_PASSWORD presente: {bool(password)} (Lunghezza: {len(password) if password else 0})")

    if not mittente or not password:
        print("-> [Email] Credenziali non configurate nei Secrets di GitHub.")
        return

    # ID univoco per evitare invii multipli della stessa partita
    id_univoco = f"{nome_torneo}_{data_target}_{riga_formattata}".replace(" ", "_")
    registro = carica_registro()
    
    if id_univoco in registro:
        print(f"-> [Email] Notifica già inviata in precedenza per questa partita. ID saltato: {id_univoco}")
        return
    else:
        print(f"-> [DEBUG EMAIL] ID univoco non presente nel registro. Procedo con l'invio.")

    oggetto = "tornei fit"
    testo = f"""È stata trovata una partita per il giocatore!

📅 Data: {data_target}
🏆 Torneo: {nome_torneo}
⏰ Dettagli: {riga_formattata}
"""

    invio_riuscito = True
    for destinatario in destinatari:
        print(f"-> [DEBUG EMAIL] Preparazione invio per destinatario: {destinatario}...")
        try:
            print("-> [DEBUG EMAIL] Connessione a smtp.gmail.com:587...")
            server = smtplib.SMTP('smtp.gmail.com', 587)
            print("-> [DEBUG EMAIL] Avvio starttls()...")
            server.starttls()
            print(f"-> [DEBUG EMAIL] Tentativo di login SMTP con utente: {mittente}...")
            server.login(mittente, password)
            print("-> [DEBUG EMAIL] Login SMTP completato con successo!")

            msg = MIMEMultipart()
            msg['From'] = mittente
            msg['To'] = destinatario
            msg['Subject'] = oggetto
            msg.attach(MIMEText(testo, 'plain'))

            print(f"-> [DEBUG EMAIL] Invio messaggio in corso verso {destinatario}...")
            server.sendmail(mittente, destinatario, msg.as_string())
            server.quit()
            print(f"-> [Email] Inviata con successo a {destinatario}!")
        except Exception as e:
            print(f"-> [Email Errore Critico] Impossibile inviare a {destinatario}: {type(e).__name__} - {e}")
            invio_riuscito = False

    if invio_riuscito:
        print(f"-> [DEBUG EMAIL] Tutti gli invii riusciti. Aggiungo al registro ID: {id_univoco}")
        registro.append(id_univoco)
        salva_registro(registro)
    else:
        print("-> [DEBUG EMAIL] Almeno un invio è fallito, il registro non viene aggiornato.")

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
    print("--- [DEBUG DATE V8] Avvio script bot_iscrizionicorsopdf.py ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        
        for cat_id, filename in CATEGORIES.items
