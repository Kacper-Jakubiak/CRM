import re
from datetime import datetime
# import ollama

class EmailClassifier:
    def __init__(self, course_names: list[str]):
        self.course_names = course_names

    def classify_category(self, process_result: dict) -> dict[str, str | bool]:
        return {
            "category": "_".join(check_course_names(self.course_names, process_result)).lower() or "other",
            "needs_response": True
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
    

# def AIanalysis(process_result: dict) -> bool:
#     """
#     Classifies whether an email needs a response using local Gemma 4 (4B) via Ollama.
#     """
#     subject = process_result.get("subject", "")
#     body = process_result.get("body", "")
#     sender = process_result.get("customer_email", "")

#     prompt = f"""You are an email classifier. Read the email below and decide if it needs a response. Answer in one word, "true" or "false".

# Email Sender: {sender}
# Email Subject: {subject}
# Email Body:
# {body}
# """

#     # Call the local Ollama instance running Gemma 4 4B
#     response = ollama.chat(
#         model='gemma4:e4b',
#         messages=[
#             {'role': 'user', 'content': prompt}
#         ],
#         options={
#             'temperature': 0.0,      # Deterministic output for classification
#             'num_predict': 10        # Keep response short
#         }
#     )

#     # Extract response text
#     response_text = response['message']['content'].strip().lower()

#     print(response_text)
#     if "true" in response_text:
#         return True
#     return False

# if __name__ == "__main__":
#    AI_result = AIanalysis({
#       "subject": "Question",
#       "body": "I need an urgent answer to my question. What is 1 + 1?",
#       "customer_email": "test@email.com"
#    })

#    print(AI_result)