from playwright.sync_api import sync_playwright

def find_courses() -> list[str]:
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto("https://szkolenia.cdsi.agh.edu.pl/")
    page.wait_for_selector(".card-col-wrapper")

    course_names = page.locator(".card-col-wrapper .card-title").all_inner_texts()

    print(f"Found {len(course_names)} courses")

    browser.close()

    return [" ".join(course_name.split()) for course_name in course_names]