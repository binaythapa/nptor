import pdfplumber
import re
import json

PDF_PATH = "questions2.pdf"
OUTPUT_JSON = "parsed_questions2.json"
START_PAGE = 1  # page 2

domain = "Snowflake"
category = "Undefined"
difficulty = "medium"

questions_output = []

with pdfplumber.open(PDF_PATH) as pdf:
    full_text = ""
    for page in pdf.pages[START_PAGE:]:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

# Remove footer links
full_text = re.sub(r'https?://\S+', '', full_text)

# Extract question blocks
question_pattern = r'(Question:\s*\d+.*?)(?=Question:\s*\d+|$)'
question_blocks = re.findall(question_pattern, full_text, re.DOTALL)

print("Total question blocks found:", len(question_blocks))

for block in question_blocks:

    # Extract answer
    answer_match = re.search(r'Answer:\s*([A-Z,\s]+)', block)
    if not answer_match:
        continue

    answer_raw = answer_match.group(1).replace(",", "").replace(" ", "")
    correct_letters = list(answer_raw)

    # 🔥 Remove explanation/reference section completely
    block = re.split(r'Explanation/Reference:', block, flags=re.IGNORECASE)[0]

    # Remove answer line
    block = re.sub(r'Answer:\s*[A-Z,\s]+', '', block)

    # Extract question text
    question_text_match = re.search(
        r'Question:\s*\d+\s*(.*?)\s*A\.',
        block,
        re.DOTALL
    )

    if not question_text_match:
        continue

    question_text = question_text_match.group(1).strip()
    question_text = re.sub(r'\s+', ' ', question_text)

    # Extract options (A-Z supported)
    parts = re.split(r'(?=[A-Z]\.)', block)

    option_list = []

    for part in parts:
        part = part.strip()

        match = re.match(r'([A-Z])\.\s*(.*)', part, re.DOTALL)
        if not match:
            continue

        letter = match.group(1)
        text = match.group(2)
        text = re.sub(r'\s+', ' ', text).strip()

        option_list.append({
            "text": text,
            "is_correct": letter in correct_letters
        })

    if len(option_list) < 2:
        continue

    questions_output.append({
        "domain": domain,
        "category": category,
        "difficulty": difficulty,
        "question": question_text,
        "options": option_list
    })

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(questions_output, f, indent=2, ensure_ascii=False)

print(f"Parsing completed! {len(questions_output)} questions extracted.")