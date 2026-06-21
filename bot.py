# --- [MIGLIORATO] Caricamento e raccolta link ---
                while await page.locator("#btn-loadMore").is_visible():
                    print("     Caricamento altri risultati...", flush=True)
                    await page.click("#btn-loadMore")
                    await asyncio.sleep(2) # Aspettiamo che il contenuto si aggiunga
                
                # Scroll finale per sicurezza
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
                
                locators = await page.locator("a[href*='Dettaglio-Competizione']").all()
                links = list(set([await loc.get_attribute("href") for loc in locators]))
                print(f"     Trovati {len(links)} tornei. Inizio analisi...", flush=True)
                
                # --- [MIGLIORATO] Processing ---
                for link in links:
                    full_url = f"https://www.fitp.it{link}"
                    
                    # Inizializziamo il torneo nel JSON IMMEDIATAMENTE
                    # Questo garantisce che se ne trovi 11, avrai 11 voci nel JSON
                    torneo_entry = {"nome": "Caricamento in corso...", "url": full_url, "date": []}
                    json_data["tornei"].append(torneo_entry)
                    
                    print(f"     -> Analizzo: {full_url}", flush=True)
                    
                    try:
                        await page.goto(full_url, wait_until="networkidle")
                        
                        # Aggiorniamo il nome vero
                        title_element = await page.locator("h1").first.text_content()
                        if title_element: torneo_entry["nome"] = title_element.strip()

                        if not await page.locator("#select-ordergame").is_visible(timeout=3000): 
                            torneo_entry["date"].append({"data": "Info", "stato": "Nessuna data disponibile"})
                            continue
                        
                        # Loop sui 2 giorni
                        for i in range(2):
                            data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                            options = await page.locator("#select-ordergame option").all_text_contents()
                            
                            if data_target not in "".join(options):
                                torneo_entry["date"].append({"data": data_target, "stato": "Nessuna pianificazione disponibile"})
                                continue
                                
                            await page.select_option("#select-ordergame", label=data_target)
                            await asyncio.sleep(2)
                            
                            async with page.expect_download(timeout=10000) as dl_info:
                                await page.click("#btnOrderGameDownload")
                            
                            path = "temp.pdf"
                            await (await dl_info.value).save_as(path)
                            nome_pdf, matches = get_pdf_info(path)
                            
                            if matches:
                                torneo_entry["date"].append({
                                    "data": data_target,
                                    "stato": "Partite trovate",
                                    "partite": [format_line_for_swift(m, date_target=data_target) for m in matches]
                                })
                                print(f"        [OK] {data_target}: {len(matches)} partite.", flush=True)
                            else:
                                torneo_entry["date"].append({"data": data_target, "stato": "Partite non trovate"})
                                print(f"        [SKIP] {data_target}: Nessuna partita.", flush=True)
                            
                            if os.path.exists(path): os.remove(path)
                            
                    except Exception as e: 
                        print(f"    !! Errore su {full_url}: {e}", flush=True)
                        torneo_entry["nome"] = "Errore durante il caricamento"
