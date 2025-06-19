import asyncio
from typing import List
from playwright.async_api import async_playwright, Page, BrowserContext
from dotenv import load_dotenv
import os
import csv
from pathlib import Path
from pydantic import BaseModel
import random
from datetime import datetime

load_dotenv()
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
NUMBER_OF_JOBS_TO_BE_SCRAPPED = 300

STORAGE_PATH = Path(__file__).parent.parent / ".storage_state.json"
SEARCH_TERM = "Software Engineer"

class Job(BaseModel):
    job_id: str
    title: str
    company: str
    job_info: str
    job_tags: list[str]
    job_description: str
    linkedin_url: str
    apply_url: str


async def login(context: BrowserContext, page: Page):
    await page.goto("https://www.linkedin.com/login")

    await page.fill("#username", LINKEDIN_EMAIL)
    await page.fill("#password", LINKEDIN_PASSWORD)
    await page.wait_for_timeout(2000)

    await page.click("button[type=submit]")
    await page.wait_for_load_state("domcontentloaded")
    print("✅ Logged in to LinkedIn.")

    # Save session cookies
    await context.storage_state(path=STORAGE_PATH)
    print(f"✅ Session cookies saved to {STORAGE_PATH}")


async def navigate_to_search_page_with_filters(page: Page, 
                                               search_term: str = SEARCH_TERM,
                                               page_num: int = 1) -> bool:
    keyword = search_term.strip().replace(' ', '%20')
    experience = "2%2C3%2C4"
    remote = "2"
    sort_by = "DD"
    start_num = str((page_num - 1) * 25)

    search_url = f"https://www.linkedin.com/jobs/search/?f_E={experience}&f_WT={remote}&keywords={keyword}&sortBy={sort_by}&start={start_num}"

    try:
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Check if the sign-in popup is present
        sign_in_popup = page.locator('button:has-text("Sign in")')

        if await sign_in_popup.is_visible():
            print("⚠️ Sign-in popup detected — login is required.")
            return False

        print("✅ Navigated to job search page without login.")
        return True

    except Exception as e:
        print(f"❌ Navigation failed: {e}")
        return False


async def collect_job_ids(page: Page):
    # Collect job cards
    job_cards = page.locator('li[data-occludable-job-id]')
    count = await job_cards.count()

    job_ids = []
    for i in range(count):
        job_id = await job_cards.nth(i).get_attribute("data-occludable-job-id")
        if job_id:
            job_ids.append(job_id)

    print(f"✅ Collected {len(job_ids)} job IDs")
    return job_ids


async def save_job_details(page: Page, jobs: dict[str, Job], job_ids: List[str]) -> None:
    for job_id in job_ids:
        if job_id in jobs:
            continue  # Skip if already scraped

        print(f"🌟 Scraping job ID: {job_id}")
        linkedin_url = f"https://www.linkedin.com/jobs/search/?currentJobId={job_id}"

        try:
            # Click the job card instead of reloading page
            card = page.locator(f'li[data-occludable-job-id="{job_id}"]')
            await card.scroll_into_view_if_needed()
            await page.wait_for_timeout(random.randint(1500, 3000))
            await card.click()
            await page.wait_for_timeout(random.randint(1500, 3000))  # Let right pane load
        except:
            continue

        # Extract job title
        try:
            title = await page.locator('h1.t-24.t-bold.inline').inner_text()
        except:
            title = "N/A"

        # Extract company name
        try:
            company = await page.locator('div.job-details-jobs-unified-top-card__company-name a').inner_text()
        except:
            company = "N/A"

        # Extract job info
        try:
            job_info = await page.locator('div.job-details-jobs-unified-top-card__primary-description-container').inner_text()
        except:
            job_info = "N/A"

        try:
            job_tags_elms = await page.locator(
                '.job-details-jobs-unified-top-card__job-insight span[dir="ltr"]'
                ).all_inner_texts()
            job_tags = [tag.strip() for tag in job_tags_elms if tag.strip()]
        except:
            job_tags = []

        # Apply URL logic
        apply_url = "" # default
        try:
            apply_button = page.locator('button.jobs-apply-button').first
            if await apply_button.is_visible():
                apply_text = (await apply_button.inner_text()).strip()
                print(f"🔹 Apply button text: {apply_text}")

                if "Easy Apply" in apply_text:
                    print(f"⚠️ Skipping Easy Apply job: {title} at {company}")
                    continue
                else:
                    try:
                        async with page.context.expect_page(timeout=3000) as popup_info:
                            await apply_button.click()
                        new_page = await popup_info.value
                        await new_page.wait_for_load_state('domcontentloaded')
                    except:
                        async with page.context.expect_page(timeout=3000) as popup_info2:
                            continue_button = page.locator("button", has_text="Continue")
                            if continue_button.is_visible():
                                await continue_button.click()
                        new_page = await popup_info2.value
                        await new_page.wait_for_load_state('domcontentloaded')

                    apply_url = new_page.url
                    print(f"🔹 Captured apply URL: {apply_url}")

                    await new_page.wait_for_timeout(random.randint(1000, 2000))
                    await new_page.close()
        except Exception as e:
            print(f"⚠️ Apply button error: {e}")
            await page.reload()
            continue

        # Extract job description
        try:
            job_description = await page.locator('div.jobs-description-content__text--stretch').inner_text()
        except:
            job_description = "N/A"

        # Debug print all fields
        print(f"🔹 Job ID: {job_id}")
        print(f"🔹 Title: {title}")
        print(f"🔹 Company: {company}")
        print(f"🔹 Job Info: {job_info}")
        print(f"🔹 Job Tags: {str(job_tags)}")
        print(f"🔹 Apply URL: {apply_url}")
        print(f"🔹 Description (first 100 chars): {job_description[:100]}...\n")

        # Save job
        job = Job(
            job_id=job_id,
            title=title.strip(),
            company=company.strip(),
            job_info=job_info.strip(),
            job_tags=job_tags,
            job_description=job_description.strip(),
            linkedin_url=linkedin_url.strip(),
            apply_url=apply_url.strip()
        )

        jobs[job_id] = job
        print(f"✅ Saved job ({len(jobs)}): {title} at {company}\n")

        await page.wait_for_timeout(random.randint(3000, 4000))

        if len(jobs) >= NUMBER_OF_JOBS_TO_BE_SCRAPPED:
            break


def save_jobs_to_csv(jobs: dict[str, Job], file_path: str = None):
    # Create the .scrapped_data directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), ".scrapped_data")
    os.makedirs(output_dir, exist_ok=True)

    # Set default file path
    if file_path is None:
        filename = f"jobs-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        file_path = os.path.join(output_dir, filename)

    fieldnames = [
        "job_id",
        "title",
        "company",
        "job_info",
        "job_tags",
        "job_description",
        "linkedin_url",
        "apply_url"
    ]

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for job in jobs.values():
            writer.writerow({
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "job_info": job.job_info,
                "job_tags": ", ".join(job.job_tags),
                "job_description": job.job_description,
                "linkedin_url": job.linkedin_url,
                "apply_url": job.apply_url
            })

    print(f"✅ Saved {len(jobs)} jobs to {file_path}")


async def main():
    async with async_playwright() as p:
        # Init page loading
        browser = await p.chromium.launch(headless=True)

        if STORAGE_PATH.exists():
            context = await browser.new_context(storage_state=str(STORAGE_PATH))
            print(f"ℹ️ Loaded storage state from {STORAGE_PATH.resolve()}")
        else:
            context = await browser.new_context()

        page = await context.new_page()

        success = await navigate_to_search_page_with_filters(page)
        if not success:
            await login(context, page)
            # Try again after login
            await navigate_to_search_page_with_filters(page)

        # Start Scrape
        jobs = dict()
        page_num = 1
        try: 
            while len(jobs) < NUMBER_OF_JOBS_TO_BE_SCRAPPED:
                job_ids = await collect_job_ids(page)
                await save_job_details(page, jobs, job_ids)
                page_num += 1
                await navigate_to_search_page_with_filters(page, SEARCH_TERM, page_num)
            
            print(f"✅ Save a total of {len(jobs)} jobs!")
        except Exception as e:
            print(f"⚠️ Error: {e}")
        finally:
            await page.wait_for_timeout(10000)
            await browser.close()
            

        save_jobs_to_csv(jobs)
        

if __name__ == "__main__":
    asyncio.run(main())
