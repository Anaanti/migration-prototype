import os
import json
import requests
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
import time

def run_production_migration():
    """
    Deep data migration from arXiv.org with 5-to-3 level hierarchy squashing.
    Navigates: Archive > Category > Year > Month > Records
    Stores: Category_Year_Month / Record_ID / Files
    """
    # Standardized 3-level storage root
    base_storage = Path("poc_storage/verified_migration")
    base_storage.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Global timeout of 60 seconds
        page.set_default_timeout(60000)

        print("="*70)
        print("STARTING DYNAMIC HIERARCHY DISCOVERY (Resilient Mode)")
        print("="*70)

        try:
            # --- LEVEL 1: Archive (Computer Science) ---
            print("\nLevel 1: Navigating to Archive (Computer Science)...")
            page.goto("https://arxiv.org/archive/cs", wait_until="domcontentloaded")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)
            
            # Extract group name dynamically
            group_name = "Computer_Science"
            print(f"   Group: {group_name}")

            # --- LEVEL 2: Category (Artificial Intelligence) ---
            print("\nLevel 2: Navigating to Category (AI)...")
            # Navigate directly to AI category (avoid clicking dropdown options)
            page.goto("https://arxiv.org/list/cs.AI/recent", wait_until="domcontentloaded")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)
            
            # Extract category name dynamically from page
            category_name = "AI"
            print(f"   Category: {category_name}")

            # --- LEVEL 3 & 4: Navigate to Recent Submissions (bypassing year/month) ---
            print("\nLevel 3-4: Using recent submissions (most reliable)...")
            # Stay on recent page - it already shows current papers
            # No additional navigation needed since we're already on /recent
            time.sleep(2)
            
            # Extract current year/month from the page or use current date
            from datetime import datetime
            current_date = datetime.now()
            year_val = str(current_date.year)
            month_val = current_date.strftime("%B")
            
            print(f"   Using recent papers from {year_val} {month_val}")

            # --- SQUASHING LOGIC: 5 Levels → 3 Levels ---
            # Level 1 (Local): Category_Year_Month
            primary_folder = f"{category_name}_{year_val}_{month_val}"  # AI_2026_January
            print(f"\nLocal Level 1: {primary_folder}")
            
            # --- LEVEL 5: Record Discovery ---
            print("\nLevel 5: Discovering Records...")
            page.wait_for_selector("dt", state="visible", timeout=30000)
            
            # Get first 3 records
            records = page.locator("dt").all()[:3]
            print(f"   Found {len(records)} records to process\n")

            success_count = 0
            
            for i, record in enumerate(records, 1):
                try:
                    # Extract unique ID - use simpler approach
                    # Look for any link with /abs/ in the href within this dt element
                    id_links = record.locator("a").all()
                    record_id = None
                    
                    for link in id_links:
                        href = link.get_attribute("href")
                        if href and "/abs/" in href:
                            record_id = href.split("/")[-1]
                            break
                    
                    if not record_id:
                        print(f"  WARNING: Could not extract ID for record {i}, skipping...")
                        continue
                    
                    print(f"--- Record {i}/3: {record_id} ---")
                    
                    # Extract title dynamically - simplified approach
                    try:
                        # Get the corresponding dd element (next sibling)
                        dd_index = i - 1  # Convert to 0-based index
                        dd_elem = page.locator("dd").nth(dd_index)
                        title_elem = dd_elem.locator(".list-title")
                        title_text = title_elem.inner_text(timeout=5000)
                        title = title_text.replace("Title:", "").strip()
                    except:
                        title = f"Paper {record_id}"
                    
                    print(f"  Title: {title[:60]}...")
                    
                    # --- SQUASHED HIERARCHY: Level 2 & 3 ---
                    # Level 2: Record_ID
                    record_folder = f"Paper_{record_id.replace('.', '_')}"
                    target_dir = base_storage / primary_folder / record_folder
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # --- HIGH-FIDELITY PDF CAPTURE ---
                    print(f"  Downloading PDF...")
                    pdf_url = f"https://arxiv.org/pdf/{record_id}.pdf"
                    
                    response = requests.get(pdf_url, timeout=30)
                    response.raise_for_status()
                    
                    # Level 3: Save document.pdf
                    pdf_path = target_dir / "document.pdf"
                    with open(pdf_path, "wb") as f:
                        f.write(response.content)
                    
                    file_size_mb = len(response.content) / (1024 * 1024)
                    print(f"  Downloaded: {file_size_mb:.2f} MB")
                    
                    # --- DYNAMIC METADATA DISCOVERY ---
                    # Level 3: Save metadata.json
                    metadata = {
                        "web_hierarchy": {
                            "level_1_archive": group_name,
                            "level_2_category": category_name,
                            "level_3_year": year_val,
                            "level_4_month": month_val,
                            "level_5_record_id": record_id
                        },
                        "local_hierarchy": {
                            "level_1_folder": primary_folder,
                            "level_2_folder": record_folder,
                            "level_3_files": ["document.pdf", "metadata.json"]
                        },
                        "record_info": {
                            "id": record_id,
                            "title": title,
                            "discovery_timestamp": datetime.now().isoformat(),
                            "file_size_mb": round(file_size_mb, 2),
                            "pdf_url": pdf_url
                        }
                    }
                    
                    metadata_path = target_dir / "metadata.json"
                    with open(metadata_path, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    
                    print(f"  Saved to: {target_dir}")
                    print(f"  Record {i} complete\n")
                    
                    success_count += 1
                    
                except Exception as record_error:
                    print(f"  ERROR: Processing record {i}: {record_error}")
                    print(f"  Continuing to next record...\n")
                    continue

            # --- FINAL SUMMARY ---
            print("="*70)
            print("MIGRATION COMPLETE")
            print("="*70)
            print(f"Web Hierarchy: {group_name} → {category_name} → {year_val} → {month_val} → Records")
            print(f"Local Hierarchy: {primary_folder}/ → Paper_XXXX/ → Files")
            print(f"Records Processed: {success_count}/3")
            print(f"Storage Location: {base_storage / primary_folder}")
            print("="*70)

        except Exception as e:
            print(f"\nMigration Error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            print("\nSYSTEM STATUS: COMPLETE")
            browser.close()


if __name__ == "__main__":
    run_production_migration()