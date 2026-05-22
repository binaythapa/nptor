python manage.py import_questions parsed_questions.json --user 1


Memory analysis in terminal

free -m


#Git 

main       → stable / production-ready
develop    → daily development
feature/*  → optional for risky features

Step 1 — Check Current Branch
git branch


Step 2 — Create develop branch
git checkout -b develop
 
Step 3 — Future Workflow
git checkout develop

git add . 
git commit -m "Sorted homepage exams by level"

Step 4 — Move Stable Code to Main
When everything is tested:

git checkout main

Then:

git merge develop


Step 5 — Optional Feature Branches

Only when needed:

git checkout develop
git checkout -b feature/payment-gateway

After complete:

git checkout develop
git merge feature/payment-gateway


###How to revert back 


git checkout develop

git restore --staged objective_exam/__init__.py





####how to push to remote

git remote -v

git push origin main

git push origin develop


####sync in cpanel

git pull origin main