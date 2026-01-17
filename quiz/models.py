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
from django.core.exceptions import ValidationError


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

        # ================= AUDIT FIELDS =================
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this question was created"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this question was last updated"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions_created"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions_updated"
    )


        # ================= DELETE TRACKING =================
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this question was deleted"
    )

    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions_deleted"
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
    TRACK = "track"
    EXAM = "exam"

    PRICING_FREE = "free"
    PRICING_MONTHLY = "monthly"
    PRICING_LIFETIME = "lifetime"

    PRICING_TYPE_CHOICES = [
        (PRICING_FREE, "Free"),
        (PRICING_MONTHLY, "Monthly"),
        (PRICING_LIFETIME, "Lifetime"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    subscription_scope = models.CharField(
        max_length=10,
        choices=[(TRACK, "Track"), (EXAM, "Exam")],
        default=TRACK
    )

    # ================= PRICING =================
    pricing_type = models.CharField(
        max_length=20,
        choices=PRICING_TYPE_CHOICES,
        default=PRICING_FREE
    )

    monthly_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Required if pricing type is Monthly"
    )

    lifetime_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Required if pricing type is Lifetime"
    )

    trial_days = models.PositiveIntegerField(
        default=7,
        help_text="Free trial duration (days)"
    )

    currency = models.CharField(max_length=10, default="INR")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ================= VALIDATION =================
    def clean(self):
    # Call parent clean
        super().clean()

        # Monthly pricing validation
        if self.pricing_type == self.PRICING_MONTHLY:
            if self.monthly_price is None:
                raise ValidationError({
                    "monthly_price": "Monthly price is required for monthly plans."
                })

        # Lifetime pricing validation
        if self.pricing_type == self.PRICING_LIFETIME:
            if self.lifetime_price is None:
                raise ValidationError({
                    "lifetime_price": "Lifetime price is required for lifetime plans."
                })


    # ================= HELPERS =================
    def is_free(self):
        return self.pricing_type == self.PRICING_FREE

    def display_price(self):
        if self.pricing_type == self.PRICING_FREE:
            return "Free"
        if self.pricing_type == self.PRICING_MONTHLY:
            return f"{self.currency} {self.monthly_price}/month"
        return f"{self.currency} {self.lifetime_price} (lifetime)"

    def __str__(self):
        return self.title


    

class ExamTrackSubscription(models.Model):
    """
    Represents user's access to an ExamTrack.
    Subscribing to a track unlocks ALL exams (levels) under it.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="track_subscriptions"
    )

    track = models.ForeignKey(
        ExamTrack,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    # Access control
    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate to revoke access without deleting history"
    )

    # Timing (future: paid plans)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Payment future-proofing
    payment_required = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    currency = models.CharField(max_length=10, default="INR")
    is_trial = models.BooleanField(default=False)
    subscribed_by_admin = models.BooleanField(
        default=False,
        help_text="Granted manually by admin"
    )



    class Meta:
        unique_together = ("user", "track")
        indexes = [
            models.Index(fields=["user", "track"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.track}"

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class Exam(models.Model):
    title = models.CharField(max_length=255)

    track = models.ForeignKey(
        "ExamTrack",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="exams"
    )

    question_count = models.PositiveIntegerField(default=10)
    duration_seconds = models.PositiveIntegerField()

    level = models.PositiveIntegerField(
        default=1,
        db_index=True
    )

    passing_score = models.FloatField(default=50.0)

    prerequisite_exams = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="unlocked_exams"
    )

    # ✅ NEW — FREE / PAID CONTROL
    is_free = models.BooleanField(
        default=True,
        help_text="If checked, this exam is free"
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Required only if exam is paid"
    )

    currency = models.CharField(
        max_length=10,
        default="INR"
    )

    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    max_mock_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Number of mock attempts allowed for this exam (0 = no mock)"
    )

    def __str__(self):
        return self.title
    

class ExamSubscription(models.Model):
    """
    Represents user's access permission to an exam.
    This is NOT an attempt.
    This is NOT an unlock by passing.
    This is the foundation for paid subscriptions.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="exam_subscriptions"
    )

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    # Access control
    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate to revoke access without deleting history"
    )

    # Timing (future use)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiry for paid / time-limited access"
    )

    # Payment future-proofing
    payment_required = models.BooleanField(
        default=False,
        help_text="Was payment required for this subscription"
    )
    payment_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Gateway payment reference (Razorpay/Stripe)"
    )
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    currency = models.CharField(
        max_length=10,
        default="INR"
    )

    subscribed_by_admin = models.BooleanField(
        default=False,
        help_text="Granted manually by admin"
    )


    class Meta:
        unique_together = ("user", "exam")
        indexes = [
            models.Index(fields=["user", "exam"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.exam}"

    def is_valid(self):
        """
        Returns True if subscription is active and not expired.
        Safe to use later in views.
        """
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)

    # ================= DISCOUNT =================
    percent_off = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Percentage discount (0–100)"
    )

    flat_off = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Flat discount amount"
    )

    # ================= APPLICABILITY =================
    track = models.ForeignKey(
        "ExamTrack",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="If set, coupon applies only to this track"
    )

    exam = models.ForeignKey(
        "Exam",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="If set, coupon applies only to this exam"
    )

    # ================= VALIDITY =================
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum times this coupon can be used"
    )

    used_count = models.PositiveIntegerField(default=0)

    # ================= TRIAL SUPPORT =================
    extra_trial_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Adds extra trial days when coupon is applied"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # ================= VALIDATION =================
    def clean(self):
        if not self.percent_off and not self.flat_off:
            raise ValidationError("Either percent_off or flat_off must be set.")

        if self.percent_off and self.percent_off > 100:
            raise ValidationError("percent_off cannot exceed 100.")

        if self.track and self.exam:
            raise ValidationError("Coupon cannot be linked to both track and exam.")

    # ================= CORE LOGIC =================
    def is_valid(self):
        now = timezone.now()

        if not self.is_active:
            return False

        if self.valid_from > now or self.valid_to < now:
            return False

        if self.usage_limit and self.used_count >= self.usage_limit:
            return False

        return True

    def mark_used(self):
        self.used_count += 1
        self.save(update_fields=["used_count"])

    def __str__(self):
        return self.code




from django.core.exceptions import ValidationError

class ExamCategoryAllocation(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="allocations"
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    percentage = models.PositiveIntegerField(default=0)
    fixed_count = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("exam", "category")

    def clean(self):
        if self.fixed_count and self.percentage:
            raise ValidationError(
                "Use either percentage OR fixed count, not both."
            )

        if self.percentage > 100:
            raise ValidationError("Percentage cannot exceed 100.")

    def __str__(self):
        return f"{self.exam} → {self.category}"





from quiz.utils import SafeStrMixin



from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

class UserExam(SafeStrMixin, models.Model):
    STATUS_STARTED = "started"
    STATUS_SUBMITTED = "submitted"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_STARTED, "Started"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_EXPIRED, "Expired"),
    ]

    # 🔐 SafeStrMixin config
    STR_FIELDS = ("user", "exam")

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

    def delete(self, *args, **kwargs):
        """
        Override delete method to handle the unique constraint with condition.
        The constraint 'one_active_attempt_per_exam' only applies when submitted_at is NULL.
        By setting submitted_at before deletion, we avoid constraint violations.
        """
        with transaction.atomic():
            # If this is an active attempt (submitted_at is NULL),
            # set submitted_at to avoid constraint violation during deletion
            if self.submitted_at is None:
                self.submitted_at = timezone.now()
                self.save(update_fields=['submitted_at'])
            
            # Now delete the object
            super().delete(*args, **kwargs)

    





class UserAnswer(models.Model):
    user_exam = models.ForeignKey(
        UserExam,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    time_spent = models.PositiveIntegerField(
    default=0,
    help_text="Time spent on this question in seconds"
)


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



class QuestionDiscussion(models.Model):
    TYPE_COMMENT = "comment"
    TYPE_DOUBT = "doubt"
    TYPE_CORRECTION = "correction"
    TYPE_EXPLANATION = "explanation"

    DISCUSSION_TYPE_CHOICES = [
        (TYPE_COMMENT, "Comment"),
        (TYPE_DOUBT, "Doubt"),
        (TYPE_CORRECTION, "Correction"),
        (TYPE_EXPLANATION, "User Explanation"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_discussions"
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="discussions"
    )

    user_exam = models.ForeignKey(
        UserExam,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="discussions"
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies"
    )

    discussion_type = models.CharField(
        max_length=20,
        choices=DISCUSSION_TYPE_CHOICES,
        default=TYPE_COMMENT
    )

    content = models.TextField()

    is_answer_incorrect = models.BooleanField(default=False)

    is_staff_verified = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_resolved = models.BooleanField(
    default=False,
    help_text="Whether staff has resolved this feedback"
    )

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ]

    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default="medium"
    )


    class Meta:
        indexes = [
            models.Index(fields=["question"]),
            models.Index(fields=["discussion_type"]),
            models.Index(fields=["is_pinned"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.discussion_type} by {self.user} on Q{self.question_id}"



class DiscussionVote(models.Model):
    UPVOTE = 1
    DOWNVOTE = -1

    VOTE_CHOICES = [
        (UPVOTE, "Upvote"),
        (DOWNVOTE, "Downvote"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    discussion = models.ForeignKey(
        QuestionDiscussion,
        on_delete=models.CASCADE,
        related_name="votes"
    )

    value = models.SmallIntegerField(choices=VOTE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "discussion")
        indexes = [
            models.Index(fields=["discussion"]),
            models.Index(fields=["value"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.value}"


class DiscussionReport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    discussion = models.ForeignKey(
        QuestionDiscussion,
        on_delete=models.CASCADE,
        related_name="reports"
    )

    reason = models.CharField(max_length=255)
    details = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "discussion")


class QuestionQualitySignal(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="quality_signals"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    is_confusing = models.BooleanField(default=False)
    explanation_helpful = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("question", "user")


#########################################################

class ContactMethod(models.Model):
    """
    Lookup table for contact methods.
    """
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
class EnrollmentLead(models.Model):
    """
    User showed intent to enroll in a paid Exam or Track.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollment_leads"
    )

    track = models.ForeignKey(
        ExamTrack,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="enrollment_leads"
    )

    exam = models.ForeignKey(
        Exam,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="enrollment_leads"
    )

    contact_method = models.ForeignKey(
        ContactMethod,
        on_delete=models.PROTECT
    )

    is_converted = models.BooleanField(
        default=False,
        help_text="Set true once subscription is granted"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        """
        Business rule enforcement (Python-level, safe everywhere)
        """
        if self.track and self.exam:
            raise ValidationError(
                "EnrollmentLead cannot have both track and exam."
            )

        if not self.track and not self.exam:
            raise ValidationError(
                "EnrollmentLead must have either track or exam."
            )

    def target_name(self):
        return self.track.title if self.track else self.exam.title

    def __str__(self):
        return f"{self.user} → {self.target_name()} ({self.contact_method})"


class PaymentRecord(models.Model):
    """
    Immutable payment history.
    One row = one payment.
    """

    PAYMENT_UPI = "upi"
    PAYMENT_BANK = "bank"
    PAYMENT_CASH = "cash"
    PAYMENT_OTHER = "other"

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_UPI, "UPI"),
        (PAYMENT_BANK, "Bank Transfer"),
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_OTHER, "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_records"
    )

    track = models.ForeignKey(
        ExamTrack,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    exam = models.ForeignKey(
        Exam,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )

    reference_id = models.CharField(
        max_length=100,
        blank=True
    )

    remarks = models.TextField(blank=True)

    paid_at = models.DateTimeField(auto_now_add=True)

    created_by_admin = models.BooleanField(default=True)

    def clean(self):
        if self.track and self.exam:
            raise ValidationError("Payment cannot be for both track and exam.")

        if not self.track and not self.exam:
            raise ValidationError("Payment must be linked to a track or exam.")

    def target_name(self):
        return self.track.title if self.track else self.exam.title

    def __str__(self):
        return f"{self.user} paid {self.amount} for {self.target_name()}"



