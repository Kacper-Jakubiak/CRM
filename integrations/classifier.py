import re
from datetime import datetime, date
from openai import OpenAI
from pydantic import BaseModel
from schemas import ProcessedEmail
from logger import logger

class EmailClassifier:
    def __init__(self, course_names: list[str], should_use_AI: bool = True):
        self.course_names = course_names
        self.client = None
        if should_use_AI:
          try:
            self.client = OpenAI()
          except Exception as e:
            logger.warning(f"Failed to log into OpenAI: {e}")
            logger.info("AI classification skipped")

    def classify_category(self, process_result: ProcessedEmail) -> tuple[str, bool]:
        stripped_body_text = strip_body(process_result.body)

        found_names = check_course_names(self.course_names, process_result.subject, stripped_body_text)
        category = "_".join(found_names).lower() or "other"
        
        if '?' in stripped_body_text:
           needs_response = True
        elif self.client is None:
           needs_response = True
        else:
           needs_response = AI_analysis(self.client, subject=process_result.subject, body=stripped_body_text, sender=process_result.customer_email)       
            
        return category, needs_response
    

def check_course_names(course_names: list[str], subject: str, body: str) -> list[str]:
  found_courses = []
  subject_lower = subject.lower()
  body_lower = body.lower()
  for course in course_names:
    course_lower = course.lower()
    if course_lower in subject_lower or course_lower in body_lower:
      found_courses.append(course)

  return found_courses


def extract_course_details(text: str) -> tuple[str, str, date]:
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    date_match = re.search(r'Termin:\s*(\d{2}\.\d{2}\.\d{4})', text)

    email_match = re.search(r'Email:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', text)

    if not lines or not date_match or not email_match:
        raise RuntimeError("Matching failed")

    normalized_course_name = re.sub(r'\s+', ' ', lines[1]).strip()

    date_obj = datetime.strptime(date_match.group(1), "%d.%m.%Y")

    return normalized_course_name, email_match.group(1), date_obj.date()
    

def strip_body(body_text: str) -> str:
    """
    Removes all lines from the text that start with '>'.
    """
    lines = body_text.split('\n')
    
    filtered_lines = [line for line in lines if not line.startswith('>')]
    
    return '\n'.join(filtered_lines)


class BooleanResponse(BaseModel):
    result: bool

def AI_analysis(client, subject: str, body: str, sender: str) -> bool:
    system_prompt = """Jesteś systemem triage dla działu obsługi klienta. 
Przeanalizuj, czy otrzymana wiadomość wymaga odpowiedzi z naszej strony. 
Jeśli nadawca pyta o informacje, wyraża zainteresowanie ofertą lub kursem, zadaje pytanie lub oczekuje odpowiedzi, zwróć True. W przeciwnym razie zwróć False.
Zwróć TYLKO słowo True lub False. Nie podawaj żadnego wyjaśnienia.

Przykłady:
- "Jestem zainteresowana kursem. Czy mogę prosić o szczegóły." -> True
- "Dziękuję za informacje. Muszę potwierdzić czy cena jest akceptowalna." -> False
- "Kiedy rusza kolejna edycja?" -> True
- "Proszę o dodatkowe informacje" -> True
- "Proszę wpisać mnie na listę" -> False"""

    user_prompt = f"""Nadawca e-maila: {sender}
Temat e-maila: {subject}
Treść e-maila:
{body}

Czy ten e-mail wymaga odpowiedzi? Odpowiedz TYLKO True lub False:"""

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=BooleanResponse,
        )
        return response.choices[0].message.parsed.result

    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        return True