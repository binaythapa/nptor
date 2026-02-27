import pdfplumber
import re
import json

PDF_PATH = "questions.pdf"
OUTPUT_JSON = "parsed_questions.json"
START_PAGE = 3

domain = "Snowflake"
category = "Undefined"
difficulty = "medium"

UNWANTED_WORDS = ["CertyIQ"]

MAX_OPTION_LENGTH = 500
MAX_QUESTION_LENGTH = 2000

questions_output = []
skipped_long = 0

with pdfplumber.open(PDF_PATH) as pdf:
    full_text = ""
    for page in pdf.pages[START_PAGE:]:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

# Remove watermark words
for word in UNWANTED_WORDS:
    full_text = full_text.replace(word, "")

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

    # Cut everything after Explanation
    block = re.split(r'Explanation:', block, flags=re.IGNORECASE)[0]

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

    # 🚨 Skip if question too long
    if len(question_text) > MAX_QUESTION_LENGTH:
        skipped_long += 1
        continue

    # Remove answer line
    block_without_answer = re.sub(r'Answer:\s*[A-Z,\s]+', '', block)

    # Extract options
    parts = re.split(r'(?=[A-Z]\.)', block_without_answer)

    option_list = []
    skip_question = False

    for part in parts:
        part = part.strip()

        match = re.match(r'([A-Z])\.\s*(.*)', part, re.DOTALL)
        if not match:
            continue

        letter = match.group(1)
        text = match.group(2)
        text = re.sub(r'\s+', ' ', text).strip()

        # 🚨 Skip if option too long
        if len(text) > MAX_OPTION_LENGTH:
            skip_question = True
            break

        option_list.append({
            "text": text,
            "is_correct": letter in correct_letters
        })

    if skip_question or len(option_list) < 2:
        skipped_long += 1
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
print(f"Skipped due to length: {skipped_long}")