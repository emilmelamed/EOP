from playwright.async_api import async_playwright, Playwright
from rich import print
import asyncio
import json
from datetime import datetime
from pathlib import Path
import time
import google.generativeai as genai
import os
import requests
#from google.colab import userdata # Import userdata

# Define a mapping for Bulgarian month abbreviations
bg_months = {
     "яну": "Jan", "фев": "Feb", "март": "Mar", "апр": "Apr",
     "май": "May", "юни": "Jun", "юли": "Jul", "авг": "Aug",
     "сеп": "Sep", "окт": "Oct", "ное": "Nov", "дек": "Dec"
 }

def notify_analysis_complete(workflow_url, repo_url):
  payload = {
      "repo_url":repo_url,
      "Status":"Analysis Complete",

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


def analyze_it_tenders_with_gemini(json_file="tenders_data.json", api_key=None):
    """
    Analyze tender data focusing on IT-related opportunities using Gemini AI.

    Args:
        json_file: Path to the JSON file containing tender data
        api_key: Google API key for Gemini (or set GOOGLE_API_KEY env variable)
    """

    try:
        # Configure Gemini
        if api_key:
          genai.configure(api_key=api_key)
        else:
          print("Warning: No API key provided for Gemini analysis.")
          return None

        model = genai.GenerativeModel('gemini-2.5-flash')

        # Load the tender data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract tenders and metadata
        tenders = data.get('tenders', [])
        metadata = data.get('metadata', {})

        print(f"\n{'='*80}")
        print("GEMINI AI ANALYSIS - IT TENDERS")
        print(f"{'='*80}")
        print(f"Loaded {len(tenders)} tenders from {json_file}")
        print(f"Starting IT-focused analysis...\n")

        # Prepare the data for Gemini
        tenders_json = json.dumps(tenders, ensure_ascii=False, indent=2)

        # Create analysis prompt focused on IT tenders
        prompt = f"""You are analyzing Bulgarian government tender data from eop.bg. Your task is to identify and analyze tenders related to Information Technologies.

DATASET METADATA:
{json.dumps(metadata, ensure_ascii=False, indent=2)}

COMPLETE TENDER DATA:
{tenders_json}

INSTRUCTIONS:
1. **Search and Filter**: Identify ALL tenders related to Information Technologies. Look for keywords in Bulgarian and English such as:
   - IT, ИТ, информационни технологии, софтуер, software, hardware, хардуер
   - Системи, systems, мрежи, networks, сървъри, servers
   - Разработка, development, внедряване, implementation
   - Кибер, cyber, сигурност, security
   - Cloud, облак, дата центрове, data centers
   - Приложения, applications, уеб, web
   - Бази данни, databases, интеграция, integration

2. **Summarize IT Tenders**: For each IT-related tender found, provide:
   - Order number and buyer
   - Brief description of what IT solution/service is needed
   - Estimated amount
   - Submission deadline
   - Link to tender

3. **Detailed Analysis**: Provide:
   - Total number of IT tenders vs total tenders
   - Total estimated value of IT tenders
   - Most common types of IT procurement (software, hardware, services, etc.)
   - Highest value IT opportunities
   - Most urgent IT tenders (deadline within 7 days)
   - Key buyers procuring IT solutions

4. **Strategic Insights**:
   - Which IT tenders are most attractive and why
   - Trends in IT procurement (types of solutions being sought)
   - Recommended tenders to prioritize for bidding

5. **Summary Table**: Create a formatted table of all IT tenders with:
   Order Number | Buyer | IT Category | Amount | Deadline | Days Left

Please provide your analysis in Bulgarian and English where appropriate."""

        print("Sending data to Gemini AI for IT tender analysis...")

        # Call Gemini API
        response = model.generate_content(prompt)

        # Get the analysis
        analysis = response.text

        # Print the analysis
        print("\n" + "="*80)
        print("ANALYSIS RESULTS")
        print("="*80)
        print(analysis)
        print("="*80)

        # Save analysis to file
        output_file = f"it_tender_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("IT TENDER DATA ANALYSIS (Gemini AI)\n")
            f.write("="*80 + "\n\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source File: {json_file}\n")
            f.write(f"Total Tenders Analyzed: {len(tenders)}\n\n")
            f.write("="*80 + "\n\n")
            f.write(analysis)

        print(f"\n✓ IT tender analysis saved to: {output_file}")
        notify_analysis_complete(
            workflow_url=os.getenv('WEBHOOK_URL'),
            repo_url=f"https://github.com/emilmelamed/EOP/blob/main/data/analyses/{output_file}"
        )
     
        return analysis

    except Exception as e:
        print(f"\n✗ Error during Gemini AI analysis: {e}")
        print("Skipping AI analysis, but scraped data is still saved.")
        return None


def quick_it_search(json_file="tenders_data.json"):
    """
    Quick local search for IT-related tenders without API call.
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tenders = data.get('tenders', [])

        # IT-related keywords in Bulgarian
        it_keywords = [
            'информационн', 'софтуер', 'хардуер', 'компютър', 'сървър',
            'мрежа', 'система', 'програм', 'данни', 'интернет',
            'уеб', 'сайт', 'облак', 'сигурност', 'кибер',
            'it', 'software', 'hardware', 'server', 'cloud'
        ]

        it_tenders = []

        for tender in tenders:
            tender_text = (
                tender.get('tender_objective', '').lower() + ' ' +
                tender.get('documentation', '').lower() + ' ' +
                tender.get('buyer', '').lower()
            )

            if any(keyword in tender_text for keyword in it_keywords):
                it_tenders.append(tender)

        print(f"\n{'='*80}")
        print(f"QUICK IT TENDER SEARCH RESULTS")
        print(f"{'='*80}")
        print(f"Found {len(it_tenders)} IT-related tenders out of {len(tenders)} total\n")

        for idx, tender in enumerate(it_tenders, 1):
            print(f"{idx}. Order: {tender.get('order_number')}")
            print(f"   Buyer: {tender.get('buyer', '')[:60]}...")
            print(f"   Objective: {tender.get('tender_objective', '')[:80]}...")
            print(f"   Amount: {tender.get('estimated_amount')}")
            print(f"   Deadline: {tender.get('submission_deadline', {}).get('formatted')}")
            print(f"   URL: {tender.get('url')}\n")

        return it_tenders
    except Exception as e:
        print(f"Error during quick IT search: {e}")
        return []


async def run_scraper(playwright: Playwright):
    start_url = "https://app.eop.bg/today"
    print(f"Navigating to {start_url}")

    async with async_playwright() as p: # Use async with to enter the context
        chrome = p.chromium # Access chromium from the context object
        browser = await chrome.launch(headless=True)
        page = await browser.new_page()
        time.sleep(60) 
        await page.goto(start_url, timeout=40000)

        print(f"Extracting ....")
        time.sleep(60) 

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

            # Process all links on the page
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

            # Check if we broke out of the inner loop due to old tender
            if found_old_tender:
                break # Break from the while loop as well

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


async def main():
    """Main function to run scraper and analysis"""

    # CONFIGURATION
    
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    RUN_QUICK_SEARCH = True  # Set to False to skip quick local search
    RUN_AI_ANALYSIS = True  if GEMINI_API_KEY else False # Set to False to skip Gemini AI analysis

    # Run the scraper
    print("\n" + "="*80)
    print("STARTING TENDER SCRAPER")
    print("="*80 + "\n")

    # Await the run_scraper function directly
    tenders = await run_scraper(async_playwright())

    print(f"\n✓ Scraping completed successfully!")
    print(f"✓ Total records scraped: {len(tenders)}")

    # Quick local IT search
    if RUN_QUICK_SEARCH:
        print("\n" + "="*80)
        print("RUNNING QUICK LOCAL IT SEARCH")
        print("="*80)
        it_tenders = quick_it_search("tenders_data.json")

    # Gemini AI Analysis
    if RUN_AI_ANALYSIS:
        if not GEMINI_API_KEY:
            print("\n" + "="*80)
            print("⚠ WARNING: No Gemini API key configured")
            print("="*80)
            print("To enable AI analysis:")
            print("1. Get API key from: https://makersuite.google.com/app/apikey")
            print("2. Add it to Colab secrets with name GOOGLE_API_KEY")
            print("="*80 + "\n")
        else:
            print("\n" + "="*80)
            print("STARTING GEMINI AI ANALYSIS")
            print("="*80)
            analyze_it_tenders_with_gemini(
                json_file="tenders_data.json",
                api_key=GEMINI_API_KEY
            )

    print("\n" + "="*80)
    print("ALL TASKS COMPLETED")
    print("="*80)
    print(f"✓ Scraped data: tenders_data.json")
    print(f"✓ AI analysis: it_tender_analysis_*.txt")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
