import os
from datetime import datetime
from playwright.sync_api import sync_playwright
import time
import random
# --- STEP 1: THE BRAIN (Path Generator) ---
def generate_ipo_path(base_dir, journal_no_raw, pub_date_raw, part_name):
    # Split "48/2025" into ID and Year
    journal_id, year = journal_no_raw.split("/")
    
    # Convert "28/11/2025" to "11_Nov"
    date_obj = datetime.strptime(pub_date_raw, "%d/%m/%Y")
    month_folder = date_obj.strftime("%m_%b")
    
    # Levels 4 and 5
    middle_layer = "Official_Patent_Records"
    part_folder = part_name.strip().replace(" ", "_")
    
    return os.path.join(base_dir, year, month_folder, f"Journal_{journal_id}", middle_layer, part_folder)

# --- THE AUTOMATION ENGINE ---
def run_automation():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(90000) #

        print("Opening IPO Journal website...")
        try:
            page.goto("https://search.ipindia.gov.in/IPOJournal/Journal/Patent", wait_until="load")
            page.wait_for_selector("table", state="visible", timeout=60000)
        except Exception as e:
            print(f"Failed to load page: {e}")
            browser.close()
            return

        rows = page.locator("table tbody tr").all()
        print(f"Total rows found: {len(rows)}")

        for i, row in enumerate(rows[:2]):
            cells = row.locator("td")
            try:
                journal_no = cells.nth(1).inner_text().strip()
                pub_date = cells.nth(2).inner_text().strip()
                print(f"\n--- Row {i+1}: Journal {journal_no} ---")

                # Find links that contain "Part" text
                pdf_links = cells.nth(4).get_by_text("Part").all()
                print(f"Found {len(pdf_links)} PDF parts.")

                for link in pdf_links:
                    part_name = link.inner_text().strip()
                    target_path = generate_ipo_path("final_storage", journal_no, pub_date, part_name)
                    
                    os.makedirs(target_path, exist_ok=True)
                    
                    # CATCH THE POPUP (The new tab where the PDF opens)
                    try:
                        print(f"Opening {part_name}...")
                        with page.context.expect_page() as popup_info:
                            link.click()
                        
                        pdf_page = popup_info.value
                        pdf_page.wait_for_load_state("load")
                        
                        # Save the PDF from the popup tab
                        save_name = f"{part_name.replace(' ', '_')}.pdf"
                        final_file_path = os.path.join(target_path, save_name)
                        
                        # Note: PDF saving works best in Chromium
                        pdf_page.pdf(path=final_file_path) 
                        print(f"Successfully saved to: {final_file_path}")
                        
                        pdf_page.close() # Close the tab to keep PC fast

                    except Exception as download_err:
                        print(f"Could not save {part_name}: {download_err}")


            except Exception as row_err:
                print(f"Skipping row {i+1} due to error: {row_err}")
            wait_time = random.uniform(4, 9) # Pick a random time between 4 and 9 seconds
            print(f"\n[Human Mode] Waiting {wait_time:.2f} seconds before the next journal...")
            time.sleep(wait_time)
        browser.close()

if __name__ == "__main__":
    run_automation()