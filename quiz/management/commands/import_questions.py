import json
from django.core.management.base import BaseCommand
from quiz.models import Domain, Category, Question, Choice
from django.utils.text import slugify
from django.db import transaction


class Command(BaseCommand):
    help = "Import questions from JSON file"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)
        parser.add_argument('--user', type=int)

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for item in data:

                domain, _ = Domain.objects.get_or_create(
                    name=item['domain'],
                    defaults={"slug": slugify(item['domain'])}
                )

                category, _ = Category.objects.get_or_create(
                    name=item['category'],
                    domain=domain,
                    defaults={"slug": slugify(item['category'])}
                )

                # 🔎 Duplicate Check
                existing = Question.objects.filter(
                    text=item['question'],
                    category=category,
                    is_deleted=False
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                correct_count = sum(
                    1 for opt in item['options'] if opt['is_correct']
                )
                total_options = len(item['options'])

                if correct_count > 1:
                    q_type = Question.MULTI
                elif total_options == 2:
                    q_type = Question.TRUE_FALSE
                else:
                    q_type = Question.SINGLE

                question = Question.objects.create(
                    text=item['question'],
                    category=category,
                    difficulty=item['difficulty'],
                    question_type=q_type,
                    is_active=True
                )

                choices = []
                for idx, opt in enumerate(item['options']):
                    choices.append(
                        Choice(
                            question=question,
                            text=opt['text'],
                            is_correct=opt['is_correct'],
                            order=idx
                        )
                    )

                Choice.objects.bulk_create(choices)
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import finished. Created: {created_count}, Skipped: {skipped_count}"
            )
            
        )