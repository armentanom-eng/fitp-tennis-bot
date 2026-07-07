# Categorie
            count = await page.locator("span:has-text('Dettaglio >')").count()
            print(f"--- [LOG] Trovate {count} categorie. Inizio estrazione ciclica ---")
            
            for i in range(count):
                # Ricarichiamo il riferimento al bottone ad ogni iterazione
                btn = page.locator("span:has-text('Dettaglio >')").nth(i)
                
                # Aggiungiamo un controllo di visibilità prima del click
                if await btn.is_visible():
                    print(f"--- [LOG] Clicco su dettaglio categoria {i+1} ---")
                    await btn.click(force=True) # force=True ignora se il bottone è coperto
                    await asyncio.sleep(3) # Pausa più lunga per caricamento pagina interna
                    
                    cat_name = await page.locator("h1.cc-title-main").first.text_content()
                    print(f"--- [LOG] Analizzo: {cat_name.strip()} ---")
                    
                    # Selettore robusto per gli iscritti
                    nomi = await page.locator(".cc-content-value .cc-title").all_text_contents()
                    print(f"--- [LOG] Trovati {len(nomi)} iscritti ---")
                    
                    # ... [Logica per popolare liste] ...
                    
                    await page.go_back()
                    # Fondamentale: attendere che la lista delle categorie riappaia
                    await page.wait_for_selector("span:has-text('Dettaglio >')")
                else:
                    print(f"--- [LOG] Bottone {i} non visibile, salto ---")
