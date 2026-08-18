import httpx
from bs4 import BeautifulSoup


def find_courses() -> list[str]:
  url = "https://szkolenia.cdsi.agh.edu.pl/"
  headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  }

  # Fetch the raw HTML content
  response = httpx.get(url, headers=headers, follow_redirects=True)
  response.raise_for_status()

  # Parse HTML
  soup = BeautifulSoup(response.text, "html.parser")

  # Select all elements matching '.card-col-wrapper .card-title'
  wrappers = soup.select(".card-col-wrapper")
  
  course_names = []
  for wrapper in wrappers:
      title_elem = wrapper.select_one(".card-title")
      if title_elem:
          text = title_elem.get_text(strip=True)
          if text:
              course_names.append(" ".join(text.split()))

  print(f"Found {len(course_names)} courses", flush=True)

  return course_names