import asyncio
import httpx
import json
from datetime import datetime

# 1. INSERISCI QUI I DATI CHE HAI RECUPERATO DAL BROWSER
API_URL = "INSERISCI_URL_API_QUI" # Es: https://www.fitp.it/api/tornei/dettaglio/12345
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    "Referer": "https://www.fitp.it/Tornei/Ricerca-tornei",
    "Cookie": "INSERISCI_IL_TUO_COOKIE_DI_SESSIONE_QUI", # Fondamentale!
    "Accept": "application/json, text/plain, */*",
}

async def estrai_iscritti_api(client, id_torneo):
    """
    Esegue una richiesta diretta all'API del server.
    """
    try:
        # Se fosse una POST, dovresti usare client.post(url, json=payload)
        response = await client.get(f"{API_URL}?id={id_torneo}", headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            # ADATTA QUESTA PARTE: il JSON di ritorno sarà strutturato in modo specifico
            # Es: return data['iscritti'] oppure data['dati']['players']
            print(f"    [LOG] Dati ricevuti per torneo {id_torneo}")
            return data 
        else:
            print(f"    [LOG] Errore API {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"    [LOG] Errore di connessione: {e}")
        return None

async def run_bot():
    print(f"--- Avvio Bot API alle {datetime.now().strftime('%H:%M:%S')} ---", flush=True)
    dati_finali = {}
    
    # Lista di ID tornei che dovrai aver recuperato prima
    lista_id_tornei = ["123", "456"] 
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for id_torneo in lista_id_tornei:
            print(f"    [LOG] Elaborazione torneo ID: {id_torneo}")
            
            iscritti = await estrai_iscritti_api(client, id_torneo)
            
            if iscritti:
                dati_finali[id_torneo] = iscritti
            
            # Pausa breve per non intasare il server (buona norma)
            await asyncio.sleep(1)
            
    # Salvataggio
    with open("Tornei_e_Iscritti_API.json", "w", encoding="utf-8") as f:
        json.dump(dati_finali, f, ensure_ascii=False, indent=4)
        
    print(f"--- Bot completato. File salvato. ---", flush=True)

if __name__ == "__main__":
    asyncio.run(run_bot())
