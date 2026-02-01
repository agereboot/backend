from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=15, unique=True,  null=True, blank=True ) 

    is_google_user = models.BooleanField(default=False)

    email_otp = models.CharField(max_length=5, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    phone_otp = models.CharField(max_length=5, blank=True, null=True)
    phone_otp_expires_at = models.DateTimeField(blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)




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
