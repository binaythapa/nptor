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



## 🔐 C. Authentication backend placement

You currently have:

<pre class="overflow-visible! px-0!" data-start="2857" data-end="3003"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-python"><span><span>AUTHENTICATION_BACKENDS = [
    </span><span>"quiz.auth_backends.EmailOrUsernameModelBackend"</span><span>,
    </span><span>"django.contrib.auth.backends.ModelBackend"</span><span>,
]
</span></span></code></div></div></pre>

### ❌ Architectural issue

You are  **moving auth to `accounts`** , but backend is still in `quiz`.

### ✅ Correct future-proof change

After migration:

<pre class="overflow-visible! px-0!" data-start="3154" data-end="3304"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-python"><span><span>AUTHENTICATION_BACKENDS = [
    </span><span>"accounts.auth_backends.EmailOrUsernameModelBackend"</span><span>,
    </span><span>"django.contrib.auth.backends.ModelBackend"</span><span>,
]
</span></span></code></div></div></pre>

📌 Not urgent, but **must be updated when accounts refactor finishes**
