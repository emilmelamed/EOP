from playwright.async_api import async_playwright, Playwright
from rich import print
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Define a mapping for Bulgarian month abbreviations
bg_months = {
     "яну": "Jan", "фев": "Feb", "март": "Mar", "апр": "Apr",
     "май": "May", "юни": "Jun", "юли": "Jul", "авг": "Aug",
     "сеп": "Sep", "окт": "Oct", "ное": "Nov", "дек": "Dec"
 }

def parse_bulgarian_date(date_string):
    """Parse Bulgarian date string and return datetime object."""
    cleaned_str = date_string.split('(')[0].strip() + date_string.split(',')[1]
    cleaned_str = cleaned_str.rstrip()
    
    # Replace Bulgarian month with English
    for bg, en in bg_months.items():
        if bg in cleaned_str:
            cleaned_str = cleaned_str.replace(bg, en)
            break
    
    return datetime.strptime(cleaned_str, "%d %b %Y %H:%M")

async def run(playwright: Playwright):
    start_url = "https://app.eop.bg/today"
    print(f"Navigating to {start_url}")
    
    chrome = playwright.chromium
    browser = await chrome.launch(headless=True)
    page = await browser.new_page()
    await page.goto(start_url, timeout=40000)

    print(f"Extracting ....")  
    
    # List to store all extracted tenders
    all_tenders = []
    skipped_old_tenders = 0
    found_old_tender = False
    page_number = 1

    while True:
        if found_old_tender:
            print(f"\n{'='*60}")
            print("✓ Reached tenders older than today - Stopping scrape")
            print(f"{'='*60}\n")
            break
        print(f"\n{'='*60}")
        print(f"Processing Page {page_number}")
        print(f"{'='*60}\n")

        emo_links = await page.locator(".nxlist-group a").all()
        emo_hrefs = []
        for link in emo_links:
            emo_hrefs.append(await link.get_attribute("href"))

        if emo_hrefs:
            print(f"Found {len(emo_hrefs)} tenders on page {page_number}")

        # Process only first 2 links (change as needed)
        for idx, link in enumerate(emo_hrefs, start=1):
            print(f"\n--- Processing tender {idx}/{len(emo_hrefs)} ---")
            
            p = await browser.new_page(base_url="https://app.eop.bg")
            
            if link is None:
                print("  Skipping link with no href attribute.")
                await p.close()
                continue
            
            print(f"  Going to {link}")
            await p.goto(link, timeout=100000)
            
            try:
                # Create a dictionary for this tender
                tender_data = {
                    "url": link,
                    "page_number": page_number,
                    "scraped_at": datetime.now().isoformat()
                }
                
                # Extract submission deadline
                submission_date = await p.locator("xpath=//*[contains(text(), 'Краен срок за подаване')]/following-sibling::*[1]").first.text_content()
                date_obj_sub = parse_bulgarian_date(submission_date)
                tender_data["submission_deadline"] = {
                    "raw": submission_date,
                    "parsed": date_obj_sub.isoformat(),
                    "formatted": date_obj_sub.strftime("%Y-%m-%d %H:%M")
                }
                print(f"  ✓ Submission deadline: {date_obj_sub}")
                
                # Extract publication date
                RFP_pub = await p.locator("xpath=//*[contains(text(), 'Дата на публикуване')]/following::div[1]").first.text_content()
                date_obj = parse_bulgarian_date(RFP_pub)
                now = datetime.now()
                
                tender_data["publication_date"] = {
                    "raw": RFP_pub,
                    "parsed": date_obj.isoformat(),
                    "formatted": date_obj.strftime("%Y-%m-%d %H:%M"),
                    "is_future": date_obj > now,
                    "is_past": date_obj < now
                }
                print(f"  ✓ Publication date: {date_obj}")
                
                # Check if publication date is today or in the future
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if date_obj < today_start:
                    print(f"  ⊗ Found old tender - published {(now - date_obj).days} days ago (before today)")
                    print(f"  ⊗ Stopping scrape - all subsequent tenders will be older")
                    skipped_old_tenders += 1
                    found_old_tender = True
                    await p.close()
                    break  # Break from the for loop
                
                print(f"  ✓ Tender is current (published today or in future)")
                
                # Extract unique order number
                order_unique_number = await p.locator("xpath=//*[contains(text(), 'Уникален номер на поръчката')]/following::div[1]").first.text_content()
                tender_data["order_number"] = order_unique_number.strip()
                print(f"  ✓ Order number: {order_unique_number}")
                
                # Extract tender method
                tender_method = await p.locator("xpath=//*[contains(text(), 'Начин на възлагане / пазарни консултации')]/following::div[1]").first.text_content()
                tender_data["tender_method"] = tender_method.strip()
                print(f"  ✓ Tender method: {tender_method}")
                
                # Extract tender objective
                tender_objective = await p.locator("xpath=//*[contains(text(), 'Обект на поръчката')]/following::div[1]").first.text_content()
                tender_data["tender_objective"] = tender_objective.strip()
                print(f"  ✓ Tender objective: {tender_objective[:50]}...")
                
                # Extract estimated amount
                estimated_amount = await p.locator("xpath=//*[contains(text(), 'Прогнозна стойност')]/following::div[1]").first.text_content()
                tender_data["estimated_amount"] = estimated_amount.strip()
                print(f"  ✓ Estimated amount: {estimated_amount}")
                
                # Extract offer opening date
                offer_opening = await p.locator("xpath=//*[contains(text(), 'Дата на отваряне на заявления/оферти')]/following::div[1]").first.text_content()
                tender_data["offer_opening"] = offer_opening.strip()
                print(f"  ✓ Offer opening: {offer_opening}")
                
                # Extract buyer info
                buyer_info = await p.locator("xpath=//*[contains(text(), 'Възложител')]/following::div[1]").first.text_content()
                tender_data["buyer"] = buyer_info.strip()
                print(f"  ✓ Buyer: {buyer_info[:50]}...")
                
                # Extract contact person
                person_contacts = await p.locator("xpath=//*[contains(text(), 'Лице за контакт')]/following::div[1]").first.text_content()
                tender_data["contact_person"] = person_contacts.strip()
                print(f"  ✓ Contact: {person_contacts[:50]}...")
                
                # Extract documentation description
                documentation_desc = await p.locator("xpath=//*[contains(text(), 'Кратко описание / документация')]/following::div[1]").first.text_content()
                tender_data["documentation"] = documentation_desc.strip()
                print(f"  ✓ Documentation: {documentation_desc[:50]}...")
                
                # Add to the list
                all_tenders.append(tender_data)
                print(f"  ✓ Tender data saved successfully")
                
            except Exception as e:
                print(f"  ✗ Error extracting data: {e}")
            
            finally:
                await p.close()
        
        # Save after each page (incremental backup)
        output_file = Path("tenders_data.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {
                    "total_tenders": len(all_tenders),
                    "skipped_old_tenders": skipped_old_tenders,
                    "pages_processed": page_number,
                    "last_updated": datetime.now().isoformat(),
                    "source_url": start_url,
                    "filter_applied": "Only tenders published today or later"
                },
                "tenders": all_tenders
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Progress saved: {len(all_tenders)} tenders in {output_file}")
        
        # Find next page
        print(f'\n<<<<< GOING TO NEXT PAGE >>>>>')
        next_button = page.locator("button[id='nx1-public-content-wrapper__nx1-published-tenders__nx1-pagination__next-page-button']")
        
        if await next_button.count() > 0 and await next_button.is_enabled():
            await next_button.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_selector(".nxlist-group a")
            page_number += 1
            print(f'<<<<< PAGE {page_number} LOADED >>>>>')
        else:
            print("\n" + "="*60)
            print("✓ No more pages available - Scraping complete!")
            print("="*60)
            break

    await browser.close()
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"SCRAPING SUMMARY")
    print(f"{'='*60}")
    print(f"Total tenders extracted: {len(all_tenders)}")
    print(f"Skipped old tenders: {skipped_old_tenders}")
    print(f"Total pages processed: {page_number}")
    print(f"Output file: {output_file.absolute()}")
    print(f"Filter: Only tenders published today or later")
    print(f"{'='*60}\n")
    
    return all_tenders


async with async_playwright() as playwright:
    tenders = await run(playwright)
    print(f"Scraping completed. Total records: {len(tenders)}")
