from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils.timezone import now
from datetime import timedelta

from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember


class Command(BaseCommand):
    help = "Send assignment reminder emails"

    def handle(self, *args, **kwargs):

        today = now()
        upcoming = today + timedelta(days=1)

        assignments = ResourceAssignment.objects.filter(
            deadline__isnull=False
        )

        for assignment in assignments:

            # 🎯 TARGET USERS
            if assignment.group:
                members = OrganizationMember.objects.filter(
                    group=assignment.group,
                    is_active=True,
                    role="student"
                )
                users = [m.user for m in members]
            else:
                users = [assignment.student]

            for user in users:

                # ⏰ REMINDER (1 day before)
                if assignment.deadline.date() == upcoming.date():

                    send_mail(
                        subject="⏰ Assignment Reminder",
                        message=f"""
Hi {user.first_name},

Reminder: You have an assignment due tomorrow.

Resource: {assignment}
Deadline: {assignment.deadline}

Please complete it on time.

Thanks
""",
                        from_email=None,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )

                # 🔴 OVERDUE
                if assignment.deadline < today:

                    send_mail(
                        subject="⚠ Assignment Overdue",
                        message=f"""
Hi {user.first_name},

Your assignment is overdue.

Resource: {assignment}
Deadline was: {assignment.deadline}

Please complete it immediately.

Thanks
""",
                        from_email=None,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )

        self.stdout.write(self.style.SUCCESS("Reminders sent successfully"))