Objective Exam - All question types sample project

Features:
- Question types: single, multi, true/false, dropdown, fill-in-the-blank, numeric, matching, ordering
- Difficulty: easy/medium/hard on Question model
- Admin inlines for Choices and advanced fields for non-MCQ types
- Single-question flow, autosave, server-side grading including partial scoring

Quick start:
1. python -m venv venv
2. source venv/bin/activate    (Windows PowerShell: .\venv\Scripts\Activate.ps1)
3. pip install -r requirements.txt
4. python manage.py makemigrations
5. python manage.py migrate
6. python manage.py createsuperuser
7. python manage.py runserver

Notes:
- For matching pairs and ordering items use JSON in admin:
  matching_pairs example: [{"left":"Apple","right":"Red"},{"left":"Banana","right":"Yellow"}]
  ordering_items example: ["Mercury","Venus","Earth","Mars"]
- This is a development scaffold. For production, configure DEBUG=False and real DB/static serving.
