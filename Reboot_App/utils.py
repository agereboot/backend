import random
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import uuid


def generate_otp():
    return str(random.randint(10000, 99999))

def otp_expiry_time():
    return timezone.now() + timedelta(minutes=5)

def send_otp_email(user, otp):
    subject = "Email Verification OTP"
    message = f"Your OTP is {otp}. It is valid for 5 minutes."

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,  # ✅ sender fixed
        recipient_list=[user.email],
        fail_silently=False
    )





def generate_reset_token(user):
    user.reset_token = uuid.uuid4()
    user.token_created_at = timezone.now()
    user.save()

    return user.reset_token


def is_token_valid(user, token):
    if str(user.reset_token) != str(token):
        return False

    if not user.token_created_at:
        return False

    expiry_time = user.token_created_at + timedelta(hours=24)

    return timezone.now() <= expiry_time


def clear_reset_token(user):
    user.reset_token = None
    user.token_created_at = None
    user.save()
