import re
from datetime import datetime
import ollama

class EmailClassifier:
    def __init__(self, course_names: list[str]):
        self.course_names = course_names

    def classify_category(self, process_result: dict) -> dict[str, str | bool]:
        return {
            "category": "_".join(check_course_names(self.course_names, process_result)).lower() or "other",
            "needs_response": AI_analysis(process_result=process_result)
        }
    

def check_course_names(course_names: list[str], process_result: dict) -> list[str]:
  subject = process_result["subject"].lower()
  body = process_result["body"].lower()

  found_courses = []
  for course in course_names:
    course_lower = course.lower()
    if course_lower in subject or course_lower in body:
      found_courses.append(course)

  return found_courses


def extract_course_details(text: str):
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    date_match = re.search(r'Termin:\s*(\d{2}\.\d{2}\.\d{4})', text)

    email_match = re.search(r'Email:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', text)

    if not lines or not date_match or not email_match:
        raise RuntimeError("Matching failed")

    normalized_course_name = re.sub(r'\s+', ' ', lines[1]).strip()
    print(repr(normalized_course_name))

    date_obj = datetime.strptime(date_match.group(1), "%d.%m.%Y")
    normalized_date = date_obj.date().isoformat()
    print(normalized_date)

    return {
        "course_name": normalized_course_name,
        "course_date": normalized_date,
        "customer_email": email_match.group(1)
    }
    

def AI_analysis(process_result: dict) -> bool:
    """
    Classifies whether an email needs a response using local Gemma 4 (4B) via Ollama.
    """
    subject = process_result.get("subject", "")
    body = process_result.get("body", "")
    sender = process_result.get("customer_email", "")

    # More explicit instruction to avoid misinterpreting test questions
    prompt = f"""You are a customer support triage system. 
Analyze if the incoming message requires a reply or assistance. 
If the sender is asking a question or expecting an answer, output True. Otherwise output False.
Output ONLY the word True or False. Always output EXACTLY one word

Email Sender: {sender}
Email Subject: {subject}
Email Body:
{body}
"""

    response = ollama.chat(
        model='gemma4:e4b',
        messages=[
            {'role': 'user', 'content': prompt}
        ],
        options={
            'temperature': 0.0,
            'num_predict': 10
        }
    )

    response_text = response['message']['content'].strip()
    print(f"DEBUG - Raw Model Output: {response_text}")

    if "false" in response_text.lower():
       return False
    return True


if __name__ == "__main__":
    AI_result = AI_analysis({
      "subject": "Pytanie o kurs",
      "body": "Potrzebuję dostać datę kursu o nazwie 'kurs_testowy.",
      "customer_email": "test@email.com"
   })

    print(AI_result)

    AI_result = AI_analysis({
      "subject": "Potwierdzenie",
      "body": "Niestety nie dam roady dotrzeć na jutro.",
      "customer_email": "test@email.com"
   })

    print(AI_result)