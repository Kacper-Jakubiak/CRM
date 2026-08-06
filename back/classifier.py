import re
from pydantic import BaseModel, Field
from openai import OpenAI
from datetime import datetime

class EmailClassifier:
    CONFIRMATION_EMAIL = "szkolenia-noreply@informatyka.agh.edu.pl"

    def __init__(self, course_names: list[str]):
        self.course_names = course_names

    def classify_category(self, process_result: dict) -> tuple[dict, dict | None]:
        if process_result["customer_email"] == EmailClassifier.CONFIRMATION_EMAIL:
            data = self.extract_course_details(process_result["body"])
            classifier_data = {
                "category": f"registered: {data['course_name']}",
                "needs_response": False
            }
            return classifier_data, data

        return AIanalysis(self.course_names, process_result), None
    
    
def check_course_names(course_names: list[str], process_result: dict) -> list[str]:
  subject = process_result["subject"].lower()
  body = process_result.get["body"].lower()

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
    

def AIanalysis(course_names: list[str], process_result: dict) -> dict:
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    )
    
    subject = process_result.get("subject", "")
    body = process_result.get("body", "")
    sender = process_result.get("customer_email", "")
    
    courses_str = "\n".join([f"- {c}" for c in course_names])

    prompt = f"""You are an email classifier. Read the email below and match it to ONE of the allowed courses, or output 'other' if it doesn't match any. Also decide if it needs a response (True or False).

Allowed Courses:
{courses_str}

Email Sender: {sender}
Email Subject: {subject}
Email Body:
{body}

Respond strictly in this format:
Category: [Exact Course Name or generic]
Needs Response: [True or False]
"""

    try:
        response = client.chat.completions.create(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )

        content = response.choices[0].message.content
        
        category = "error"
        needs_response = True
        
        for line in content.split("\n"):
            if line.lower().startswith("category:"):
                category = line.split(":", 1)[1].strip()
            elif line.lower().startswith("needs response:"):
                val = line.split(":", 1)[1].strip().lower()
                needs_response = "true" in val

        return {
            "category": category,
            "needs_response": needs_response
        }

    except Exception as e:
        print(f"Local AI analysis error: {e}")
        return {
            "category": "error",
            "needs_response": True
        }