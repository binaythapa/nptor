from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.utils import timezone
from phone_field import PhoneField
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models import Q
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q

User = get_user_model()

from django.conf import settings


class Client(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    contact= PhoneField(blank=True, help_text='Contact phone number', null= True)
    address = models.CharField(max_length=200, blank=True, null=True)
    acceptpolicy= models.BooleanField(default=False)

    def __str__(self):
        return str(self.user)

    def fullname(self):
        return str(self.user.first_name + " " + self.user.last_name)
    

class Notification(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, help_text='Leave empty to target all users (broadcast).')
    is_read_by = models.JSONField(default=dict, blank=True, help_text='map user_id->true')

    def mark_read(self, user):
        d = self.is_read_by or {}
        d[str(user.id)] = True
        self.is_read_by = d
        self.save()

    def unread_for(self, user):
        return not self.is_read_by.get(str(user.id), False)
    

 # =====================================================
# DOMAIN (Snowflake, Power BI, Tableau)
# =====================================================
class Domain(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)  
    is_active = models.BooleanField(default=True)  

    def __str__(self):
        return self.name   


class Category(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE,null=True,blank=True,related_name="categories")
    name = models.CharField(max_length=200, default= 'Unknown')
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ("domain", "slug")
    # optionally store a description or metadata
    def __str__(self):
        # show hierarchy in admin list
        return (self.parent.name + ' -> ' if self.parent else '') + self.name

    def get_descendants_include_self(self):
        """
        Return a queryset/list of category IDs including this category and all descendants.
        Simple recursive implementation.
        """
        ids = [self.id]
        children = list(self.children.all())
        for c in children:
            ids.extend(c.get_descendants_include_self())
        return ids
 
class Question(models.Model):
    SINGLE = 'single'
    MULTI = 'multi'
    TRUE_FALSE = 'tf'
    DROPDOWN = 'dropdown'
    FILL_BLANK = 'fill'
    NUMERIC = 'numeric'
    MATCHING = 'match'
    ORDERING = 'order'
    QUESTION_TYPES = [
        (SINGLE, 'Single choice'),
        (MULTI, 'Multiple choice'),
        (TRUE_FALSE, 'True/False'),
        (DROPDOWN, 'Dropdown'),
        (FILL_BLANK, 'Fill in the blank'),
        (NUMERIC, 'Numeric answer'),
        (MATCHING, 'Matching (pair)'),
        (ORDERING, 'Ordering'),
    ] 
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'   
    DIFFICULTY_CHOICES = [(EASY,'Easy'),(MEDIUM,'Medium'),(HARD,'Hard')]
    is_active = models.BooleanField(default=True)
    
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,      
    ) 

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='questions',
        null=True,
        blank=True
    )
    text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default=SINGLE
    )

    # NEW – detailed explanation / solution, visible on result page
    explanation = models.TextField(
        blank=True,
        null=True,
        help_text='Optional detailed explanation or solution shown on the result page.'
    )

    correct_text = models.TextField(
        blank=True,
        null=True,
        help_text='Correct text for fill-in'
    )
    numeric_answer = models.FloatField(
        blank=True,
        null=True,
        help_text='Numeric correct answer'
    )
    numeric_tolerance = models.FloatField(
        default=0.0,
        help_text='Tolerance for numeric answer'
    )

    matching_pairs = models.JSONField(
        blank=True,
        null=True,
        help_text='List of {"left":"A","right":"1"}'
    )
    ordering_items = models.JSONField(
        blank=True,
        null=True,
        help_text='List of canonical ordering items'
    )

    def __str__(self):
        return (self.text[:75] + '...') if len(self.text) > 75 else self.text
    
    
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    def __str__(self): return self.text




class QuestionFeedback(models.Model):
    STATUS_NEW = 'new'
    STATUS_REVIEWED = 'reviewed'
    STATUS_RESOLVED = 'resolved'
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_REVIEWED, 'Reviewed'),
        (STATUS_RESOLVED, 'Resolved'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='question_feedbacks'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    user_exam = models.ForeignKey(
        'UserExam',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='question_feedbacks'
    )

    # student’s comment
    comment = models.TextField(blank=True)

    # tick if they think the official answer/options are wrong
    is_answer_incorrect = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW
    )
    staff_note = models.TextField(blank=True)

    def __str__(self):
        label = "Incorrect-answer report" if self.is_answer_incorrect else "Comment"
        return f"{label} by {self.user} on Q#{self.question_id}"



class PracticeStat(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="practice_stats"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    total_attempted = models.PositiveIntegerField(default=0)
    total_correct = models.PositiveIntegerField(default=0)

    last_practice_date = models.DateField(null=True, blank=True)
    streak = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "category")

    def accuracy(self):
        if self.total_attempted == 0:
            return 0
        return round((self.total_correct / self.total_attempted) * 100, 2)

    def __str__(self):
        return f"{self.user} | {self.category} | {self.total_correct}/{self.total_attempted}"
    


# =====================================================
# DIFFICULTY 
# =====================================================
class Difficulty(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)   # ✅ ADD THIS    
    is_active = models.BooleanField(default=True)   

    def __str__(self):
        return self.name
    






##########################################################
##########EXAM MANAGEMENT
##########################################################

class ExamTrack(models.Model):
    """
    Parent container like:
    - SnowPro Core
    - SnowPro Advanced
    - SQL Analyst Track
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ ADD THIS

    def __str__(self):
        return self.title

class Exam(models.Model):
    title = models.CharField(max_length=255)

    # ✅ NEW: Parent Exam Track (SnowPro Core, etc.)
    track = models.ForeignKey(
        "ExamTrack",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams",
        help_text="Parent exam track like SnowPro Core"
    )

    # Legacy single category
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Future-proof multi-category
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="exams"
    )

    question_count = models.PositiveIntegerField(default=10)
    duration_seconds = models.PositiveIntegerField()

    level = models.PositiveIntegerField(
        default=1,
        db_index=True,
        help_text="1=Beginner, 2=Intermediate, 3=Advanced"
    )

    passing_score = models.FloatField(
        default=50.0,
        help_text="Percentage required to pass"
    )

    prerequisite_exams = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="unlocked_exams"
    )

    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ExamCategoryAllocation(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="allocations"
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    percentage = models.PositiveIntegerField(
        default=0,
        help_text="0–100"
    )

    fixed_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Overrides percentage if set"
    )

    class Meta:
        unique_together = ("exam", "category")
        constraints = [
            # percentage must be between 0 and 100
            models.CheckConstraint(
                condition=Q(percentage__gte=0) & Q(percentage__lte=100),
                name="exam_alloc_percentage_between_0_100"
            ),

            # cannot have both fixed_count and percentage > 0
            models.CheckConstraint(
                condition=Q(fixed_count__isnull=True) | Q(percentage=0),
                name="exam_alloc_fixed_or_percentage"
            ),
        ]

    def clean(self):
        if self.fixed_count is not None and self.percentage > 0:
            raise ValidationError(
                "Use either percentage OR fixed count, not both."
            )

    def __str__(self):
        return f"{self.exam} → {self.category}"


class UserExam(models.Model):
    STATUS_STARTED = "started"
    STATUS_SUBMITTED = "submitted"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_STARTED, "Started"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_EXPIRED, "Expired"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_STARTED,
        db_index=True
    )

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    question_order = models.JSONField(
        default=list,
        help_text="Ordered list of question IDs"
    )
    current_index = models.PositiveIntegerField(default=0)

    score = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "exam"]),
            models.Index(fields=["user", "submitted_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "exam"],
                condition=Q(submitted_at__isnull=True),
                name="one_active_attempt_per_exam"
            )
        ]

    def time_remaining(self):
        elapsed = (timezone.now() - self.started_at).total_seconds()
        return max(0, int(self.exam.duration_seconds - elapsed))

    def is_active(self):
        return self.status == self.STATUS_STARTED and self.time_remaining() > 0

    def mark_expired(self):
        if self.status == self.STATUS_STARTED:
            self.status = self.STATUS_EXPIRED
            self.submitted_at = timezone.now()
            self.passed = False
            self.save(update_fields=["status", "submitted_at", "passed"])

    def submit(self, score, is_mock=False):
        self.score = score
        self.submitted_at = timezone.now()
        self.status = self.STATUS_SUBMITTED
        self.passed = None if is_mock else (score >= self.exam.passing_score)
        self.save()

    def __str__(self):
        return f"{self.user} → {self.exam}"

class UserAnswer(models.Model):
    user_exam = models.ForeignKey(
        UserExam,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    choice = models.ForeignKey(
        Choice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    selections = models.JSONField(null=True, blank=True)
    raw_answer = models.TextField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ("user_exam", "question")
        indexes = [
            models.Index(fields=["user_exam", "question"]),
        ]

    def __str__(self):
        return f"UE:{self.user_exam_id} Q:{self.question_id}"





class ExamGrader:
    @staticmethod
    def grade(user_exam: UserExam):
        correct = 0
        total = user_exam.answers.count()

        for ans in user_exam.answers.select_related("question", "choice"):
            q = ans.question

            if q.question_type == Question.SINGLE:
                ans.is_correct = ans.choice and ans.choice.is_correct

            elif q.question_type == Question.TRUE_FALSE:
                ans.is_correct = ans.choice and ans.choice.is_correct

            elif q.question_type == Question.MULTI:
                correct_ids = set(
                    q.choices.filter(is_correct=True).values_list("id", flat=True)
                )
                selected_ids = set(ans.selections or [])
                ans.is_correct = selected_ids == correct_ids

            elif q.question_type == Question.NUMERIC:
                if ans.raw_answer is not None:
                    diff = abs(float(ans.raw_answer) - q.numeric_answer)
                    ans.is_correct = diff <= q.numeric_tolerance

            else:
                ans.is_correct = False

            if ans.is_correct:
                correct += 1

            ans.save()

        score = round((correct / total) * 100, 2) if total else 0
        user_exam.submit(score)
        return score







class ExamAdminValidator:
    @staticmethod
    def validate_exam(exam: Exam):
        allocations = exam.allocations.all()

        fixed_total = sum(
            a.fixed_count or 0 for a in allocations
        )

        percent_total = sum(
            a.percentage for a in allocations if a.fixed_count is None
        )

        if fixed_total > exam.question_count:
            raise ValidationError("Fixed allocation exceeds total questions")

        if percent_total > 100:
            raise ValidationError("Percentage allocation exceeds 100%")
        


class ExamUnlockLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)

    unlocked_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(
        max_length=30,
        default="exam_pass"
    )

    class Meta:
        unique_together = ("user", "exam")

    def __str__(self):
        return f"{self.user} unlocked {self.exam}"


####################################################################################################