from playwright.sync_api import sync_playwright
import requests

ADD_COURSE_API_URL = "http://127.0.0.1:8000/api/add_course"

def add_courses(course_names: list[str]):
    for course_name in course_names:
      response = requests.post(ADD_COURSE_API_URL, params={"course_name": course_name})
      print(f"Status: {response.status_code} | Response: {response.json()}")

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


if __name__ == "__main__":
  add_courses(find_courses())