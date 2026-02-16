from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver



class Role(models.Model):
    ROLE_CHOICES = (
        ("super_admin", "Super Admin"),
        ("hr_admin", "HR Admin"),
        ("employee", "Employee"),
    )

    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)

    def __str__(self):
        return self.name


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Location(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="locations"
    )
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("company", "name")

    def __str__(self):
        return f"{self.company.name} - {self.name}"

class Department(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.company.name} - {self.name}"

class Plan(models.Model):
    PLAN_CHOICES = (
        ("basic", "Basic"),
        ("premium", "Premium"),
        ("gold", "Gold"),
    )

    name = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.IntegerField()
    features = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    INVITE_STATUS = (
        ("invited", "Invited"),
        ("Registered", "Registered"),
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("deactivated", "Deactivated"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=15, null=True, blank=True ) 

    is_google_user = models.BooleanField(default=False)
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True
    )
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    invite_status = models.CharField(
        max_length=20, choices=INVITE_STATUS, default="invited"
    )
    password_reset_required = models.BooleanField(default=True)


    email_otp = models.CharField(max_length=5, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    phone_otp = models.CharField(max_length=5, blank=True, null=True)
    phone_otp_expires_at = models.DateTimeField(blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    reset_token = models.UUIDField(null=True, blank=True)
    token_created_at = models.DateTimeField(null=True, blank=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class EmployeePlan(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    assigned_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"


class Question(models.Model):
    QUESTION_TYPES = (
        ("single_choice", "Single Choice"),
        ("number", "Number"),
        ("date", "Date"),
        ("slider", "Slider"),
    )

    text = models.CharField(max_length=255)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    order = models.PositiveIntegerField()
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return self.text

class QuestionOption(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="options"
    )
    label = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.question.text} - {self.label}"


class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    # for single choice
    selected_option = models.ForeignKey(
        QuestionOption, null=True, blank=True, on_delete=models.SET_NULL
    )

    # for number / slider
    answer_number = models.FloatField(null=True, blank=True)

    # for date
    answer_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "question")
