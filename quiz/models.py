from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from phone_field import PhoneField
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
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=200)
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
    
# New model: ExamCategoryAllocation
class ExamCategoryAllocation(models.Model):
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE, related_name='allocations')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    # percentage defined as integer 0..100 (sum of percentages for exam should be 100 or less)
    percentage = models.PositiveIntegerField(default=0, help_text='Percentage of exam questions from this category (0-100)')
    # optional absolute count preference (if set, treat as fixed count for allocation)
    fixed_count = models.PositiveIntegerField(null=True, blank=True, help_text='If set, allocate this many questions instead of using percentage')

    class Meta:
        unique_together = ('exam','category')
        ordering = ('id',)

    def __str__(self):
        return f"{self.exam.title} - {self.category.name}: {self.percentage}%{' / ' + str(self.fixed_count) if self.fixed_count else ''}"

# =====================================================
# DIFFICULTY 
# =====================================================
class Difficulty(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)   # ✅ ADD THIS    
    is_active = models.BooleanField(default=True)   

    def __str__(self):
        return self.name


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



   
    '''
    difficulty = models.ForeignKey(
        Difficulty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
        help_text="Leave empty if difficulty is undefined"
    )
    '''

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


from django.contrib.auth.models import User

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





class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    def __str__(self): return self.text

# quiz/models.py (excerpt - update Exam model)
class Exam(models.Model):
    title = models.CharField(max_length=255)
    # legacy single category (kept for backward compatibility)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    # new: allow selecting multiple categories on the exam directly
    categories = models.ManyToManyField(Category, blank=True, related_name='exams')
    question_count = models.PositiveIntegerField(default=10)
    duration_seconds = models.PositiveIntegerField()
    is_published = models.BooleanField(default=False)

        # NEW — progression level and passing threshold (add these lines)
    level = models.PositiveIntegerField(
        default=1,
        help_text='Progression level for this exam (1 = beginner).'
    )
    passing_score = models.FloatField(
        default=50.0,
        help_text='Percentage required to pass (0-100).'
    )

    # NEW — explicit prerequisites
    prerequisite_exams = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='dependent_exams',
        help_text='If set, user must pass these exams before taking this exam.'
    )


    def __str__(self):
        return self.title

class UserExam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    question_order = models.JSONField(null=True, blank=True)
    current_index = models.IntegerField(default=0)
        # NEW — whether this attempt is a passing one
    passed = models.BooleanField(null=True, blank=True, help_text='True if this attempt passed according to exam.passing_score')

    def is_active(self):
        if self.submitted_at: return False
        elapsed = (timezone.now() - self.started_at).total_seconds()
        return elapsed < self.exam.duration_seconds
    def time_remaining(self):
        elapsed = (timezone.now() - self.started_at).total_seconds()
        remaining = int(self.exam.duration_seconds - elapsed)
        return max(0, remaining)
    def __str__(self): return f"{self.user} - {self.exam}"

class UserAnswer(models.Model):
    user_exam = models.ForeignKey(UserExam, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    selections = models.JSONField(null=True, blank=True, help_text='For multi/match/order store user selections')
    raw_answer = models.TextField(null=True, blank=True)
    def __str__(self): return f"Ans: {self.user_exam.id} - Q{self.question.id}"



from django.conf import settings
from django.db import models
from django.utils import timezone

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

