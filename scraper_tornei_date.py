if await page.locator(dropdown_selector).is_visible():
                    # Caso: Dropdown presente - Modificato solo il range a (0, 2) per Oggi e Domani
                    for i in range(0, 2):
                        data_target = (datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y")
                        
                        # Verifica se la data esiste nel menu
                        if await page.locator(f"{dropdown_selector} option:has-text('{data_target}')").count() > 0:
                            await page.select_option(dropdown_selector, label=data_target)
                            await asyncio.sleep(3)
                            
                            if await download_btn.is_visible():
                                async with page.expect_download() as dl_info: 
                                    await download_btn.click()
                                download = await dl_info.value
                                await download.save_as("temp.pdf")
                                matches = get_pdf_info("temp.pdf")
                                json_data["tornei"].append({
                                    "url": full_url, 
                                    "nomeTorneo": nome_torneo.strip(), 
                                    "data": data_target, 
                                    "partite": [format_line_for_swift(m, data_target) for m in matches] if matches else ["Nessuna partita trovata"]
                                })
