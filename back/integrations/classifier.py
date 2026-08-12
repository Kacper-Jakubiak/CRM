import re
from datetime import datetime
import ollama

class EmailClassifier:
    def __init__(self, course_names: list[str]):
        self.course_names = course_names

    def classify_category(self, process_result: dict[str, str]) -> dict[str, str | bool]:
        category = "_".join(check_course_names(self.course_names, process_result)).lower() or "other"

        stripped_body_text = strip_body(process_result["body"])

        # AI_topics_result = AI_topics(subject=process_result["subject"], body=stripped_body_text, sender=process_result["customer_email"])
        # print(AI_topics_result)

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
    # print(repr(normalized_course_name))

    date_obj = datetime.strptime(date_match.group(1), "%d.%m.%Y")
    normalized_date = date_obj.date().isoformat()
    # print(normalized_date)

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
    # print(f"DEBUG - Raw Model Output: '{response_text}'")

    if not response_text:
        print("DEBUG - Model returned empty string. Defaulting to True.")
        return True 

    if "false" in response_text.lower():
       return False
       
    return True


def AI_topics(subject: str, body: str, sender: str) -> str | None:
    """
    Extracts the course subject/topic the sender is interested in.
    Returns the topic as a short phrase, or None if no course subject
    is mentioned or requested.
    """

    prompt = f"""
You are a customer support email analysis system.

Analyze the email and determine whether the sender is asking about,
interested in, or referring to the SUBJECT MATTER of a course.

By "topic", I mean the actual subject/content being taught in the course,
NOT administrative information.

Examples of course subject topics:
- psychotherapy
- cognitive behavioral therapy
- stress management
- ADHD diagnosis
- project management
- accounting
- digital marketing

Do NOT return topics such as:
- price
- cost
- dates
- schedule
- duration
- registration
- availability
- location
- certificate
- payment

Email Sender: {sender}
Email Subject: {subject}
Email Body:
{body}

Course subject/topic, provide a short keyword answer:
"""

    response = ollama.chat(
        model="qwen2.5:7b",
        messages=[
            {"role": "user", "content": prompt}
        ],
        options={
            "temperature": 0.0,
            "num_predict": 50,
        },
    )

    # print(response)
    response_text = response["message"]["content"].strip()

    if not response_text or response_text.lower() == "none":
        return None

    return response_text


if __name__ == "__main__":
    AI_result = AI_topics(
      "Re: [EXT] Szkolenia z AI",
      """Dzień dobry,
jestem studentką V roku i chciałam zapytać o kurs Python dla Wszystkich: 
Od Podstaw do Eksperta. Czy można zapisać się na ten kurs i w jakich 
terminach się odbywa? Czy ukończenie kursu wiąże się z otrzymaniem 
certyfikatu?

Z wyrazami szacunku,
Patrycja Rzeszut
""",
      "test@email.com")

    print(AI_result)
    pass