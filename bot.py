import pdfplumber
import os
import re
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

def estrai_dati_pdf(percorso_pdf):
    """Legge il PDF e formatta le righe: Nome1; Nome2; Orario"""
    partite = []
    with pdfplumber.open(percorso_pdf) as pdf:
        text = pdf.pages[0].extract_text()
        if not text: return None, []
        
        # Estrai nome circolo (solitamente riga 2)
        righe = text.split('\n')
        nome_circolo = righe[1] if len(righe) > 1 else "Circolo sconosciuto"
        
        # Regex per trovare: Inizio ore, Giocatore1, vs, Giocatore2
        # Cerca pattern: Inizio ore: XX:XX [a capo] Nome1 [a capo] vs [a capo] Nome2
        matches = re.findall(r"Inizio ore: (\d{2}:\d{2}).*?\n(.*?)\nvs\n(.*?)\n", text)
        
        for orario, g1, g2 in matches:
            partite.append(f"{g1.strip()}; {g2.strip()}; {orario}")
            
    return nome_circolo, partite

def elabora_torneo(page, url, data_target):
    page.goto(url, wait_until="networkidle")
    
    # Selezione data nel dropdown (adatta il selettore se necessario)
    # page.select_option("select[name='data_gioco']", value=data_target) 
    
    try:
        # Scarica PDF
        with page.expect_download(timeout=10000) as download_info:
            page.click("#btnOrderGameDownload")
        download = download_info.value
        path = f"temp.pdf"
        download.save_as(path)
        
        # Processa
        circolo, partite = estrai_dati_pdf(path)
        os.remove(path)
        return circolo, partite
    except:
        return None, None

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Date
        oggi = date.today().strftime("%d/%m/%Y")
        domani = (date.today() + timedelta(days=1)).strftime("%d/%m/%Y")
        
        # Qui dovresti avere la lista degli URL dei tornei (che avevi già estratto)
        lista_tornei = ["URL_TORNEO_1", "URL_TORNEO_2"] 
        
        with open("Report_Partite.txt", "w", encoding="utf-8") as f:
            for url in lista_tornei:
                for d in [oggi, domani]:
                    circolo, partite = elabora_torneo(page, url, d)
                    
                    if circolo:
                        f.write(f"\n--- {circolo} ({d}) ---\n")
                        if partite:
                            f.write("\n".join(partite) + "\n")
                        else:
                            f.write("Nessuna partita programmata.\n")
                    else:
                        f.write(f"\n--- {d}: Elenco partite non ancora creato ---\n")
        
        browser.close()

if __name__ == "__main__":
    run()
