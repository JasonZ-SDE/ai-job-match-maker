import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
STORAGE_PATH = Path(__file__).parent.parent / ".storage_state.json"
SEARCH_TERM = "Software Engineer"

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


async def main():
    async with async_playwright() as p:
        # Init page loading
        browser = await p.chromium.launch(headless=False)

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


        await page.wait_for_timeout(1000000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
    