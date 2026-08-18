import requests
from requests.exceptions import RequestException
from logger import logger

URL = "https://szkolenia.cdsi.agh.edu.pl/api/courses/search/?q="
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://szkolenia.cdsi.agh.edu.pl/",
    "Accept": "application/json, text/plain, */*",
}


def fetch_course_names(timeout: int = 10) -> list[str] | None:
    """Fetches course names from AGH API safely.
    
    Returns an empty list if network, status, or parsing errors occur.
    """
    logger.info("Initiating course search fetch from AGH API")

    try:
        response = requests.get(URL, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except RequestException as e:
        logger.error(f"HTTP request to course API failed: {e}")
        return None
    except ValueError as e:
        logger.error(f"Failed to parse JSON response from AGH API: {e}")
        return None

    courses_list = data.get("courses")
    if not isinstance(courses_list, list):
        logger.warning(f"Unexpected JSON structure received. 'courses' key is not a list: {type(courses_list)}")
        return None

    names = []
    for item in courses_list:
        if isinstance(item, dict) and item.get("name"):
            clean_name = str(item["name"]).replace("\xa0", " ").strip()
            names.append(clean_name)
        else:
            logger.warning(f"Skipping invalid course entry: {item}")

    logger.info(f"Found {len(names)} course names")
    return names


if __name__ == "__main__":
    courses = fetch_course_names()
    print(courses)