import re
from datetime import datetime
import ollama

class EmailClassifier:
    def __init__(self, course_names: list[str]):
        self.course_names = course_names

    def classify_category(self, process_result: dict[str, str]) -> dict[str, str | bool]:
        category = "_".join(check_course_names(self.course_names, process_result)).lower() or "other"

        stripped_body_text = strip_body(process_result["body"])

        if '?' in stripped_body_text:
           needs_response = True
        else:
           needs_response = AI_analysis(subject=process_result["subject"], body=stripped_body_text, sender=process_result["customer_email"])       
            
        return {
            "category": category,
            "needs_response": needs_response
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
    

def strip_body(body_text: str) -> str:
    """
    Removes all lines from the text that start with '>'.
    """
    lines = body_text.split('\n')
    
    filtered_lines = [line for line in lines if not line.startswith('>')]
    
    return '\n'.join(filtered_lines)


def AI_analysis(subject: str, body: str, sender: str) -> bool:
    """
    Classifies whether an email needs a response using local LLM.
    """

    prompt = f"""You are a customer support triage system. 
Analyze if the incoming message requires a reply from our side. 
If the sender is asking for information, expressing interest in an offer/course, asking a question, or expecting an answer, output True. Otherwise output False.
Output ONLY the word True or False. Do not provide any explanation.

Examples:
- "Jestem zainteresowana kursem. Czy mogę prosić o szczegóły." -> True
- "Dziękuję za informacje. Muszę potwierdzić czy cena jest akceptowalna." -> False
- "Kiedy rusza kolejna edycja?" -> True
- "Proszę o dodatkowe informacje" -> True

Email Sender: {sender}
Email Subject: {subject}
Email Body:
{body}

Does this email require a response? Output ONLY True or False:"""

    response = ollama.chat(
        model='qwen2.5:7b',
        messages=[
            {'role': 'user', 'content': prompt}
        ],
        options={
            'temperature': 0.0,
            'num_predict': 50
        }
    )

    response_text = response['message']['content'].strip()
    print(f"DEBUG - Raw Model Output: '{response_text}'")

    if not response_text:
        print("DEBUG - Model returned empty string. Defaulting to True.")
        return True 

    if "false" in response_text.lower():
       return False
       
    return True

if __name__ == "__main__":
    AI_result = AI_analysis({
      "subject": "Re: [EXT] Szkolenia z AI",
      "body": """Dzień dobry,
Dziękuję za informacje. Muszę potwierdzić czy  cena jest dla nas akceptowalna. Odezwę się w nabliższym czasie. 
Pozdrawiam,
Paulina Stawowiak
""",
      "customer_email": "test@email.com"
   })

    print(AI_result)

    AI_result = AI_analysis({
      "subject": "Potwierdzenie",
      "body": "Niestety nie dam roady dotrzeć na jutro.",
      "customer_email": "test@email.com"
   })

    print(AI_result)