import pdfplumber
import re
import json

PDF_PATH = "questions3.pdf"
OUTPUT_JSON = "parsed_questions3.json"
START_PAGE = 0  # adjust if needed

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

# Extract question blocks
question_pattern = r'(Question\s+\d+:.*?)(?=Question\s+\d+:|$)'
question_blocks = re.findall(question_pattern, full_text, re.DOTALL)

print("Total question blocks found:", len(question_blocks))

for block in question_blocks:

    # Remove "Skipped"
    block = block.replace("Skipped", "")

    # Cut explanation section
    block = re.split(r'Explanation', block, flags=re.IGNORECASE)[0]

    # Extract question text
    question_match = re.search(
        r'Question\s+\d+:\s*(.*?)(?=\n\s*\n|\n\s*[A-Z_]+|\n\s*TRUE|\n\s*FALSE)',
        block,
        re.DOTALL
    )

    if not question_match:
        continue

    question_text = question_match.group(1).strip()
    question_text = re.sub(r'\s+', ' ', question_text)

    # Extract option lines
    lines = block.split("\n")
    option_list = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # Skip Question header
        if line.startswith("Question"):
            continue

        # Skip explanation
        if line.startswith("Explanation"):
            continue

        # Skip the question text itself
        if question_text in line:
            continue

        # Detect correct
        is_correct = "(Correct)" in line

        # Clean option text
        clean_text = line.replace("(Correct)", "").strip()

        # Skip short junk lines
        if len(clean_text) < 3:
            continue

        # Skip if it's explanation text accidentally
        if clean_text.lower().startswith("explanation"):
            continue

        # Add only meaningful option lines
        if clean_text.isupper() or "_" in clean_text or clean_text in ["TRUE", "FALSE"]:
            option_list.append({
                "text": clean_text,
                "is_correct": is_correct
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