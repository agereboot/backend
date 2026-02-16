import random
import string
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail

from .models import Location, Department, EmployeePlan


# ===============================
# GENERATE USERNAME
# ===============================
def generate_username(first_name, last_name):
    base = f"{first_name}{last_name}".lower().replace(" ", "")
    random_number = random.randint(100, 999)
    return f"{base}{random_number}"


# ===============================
# GENERATE TEMP PASSWORD
# ===============================
def generate_temp_password():
    return "".join(random.choices(string.ascii_letters + string.digits, k=8))


# ===============================
# CREATE LOCATION / DEPARTMENT
# ===============================
def get_location_department(company, location_name, department_name):

    location = None
    department = None

    if location_name:
        location_name = location_name.strip().title()

        location = Location.objects.filter(
            name__iexact=location_name,
            company=company
        ).first()

        if not location:
            location = Location.objects.create(
                name=location_name,
                company=company,
            )

    if department_name:
        department_name = department_name.strip().title()

        department = Department.objects.filter(
            name__iexact=department_name,
            company=company
        ).first()

        if not department:
            department = Department.objects.create(
                name=department_name,
                company=company,
            )

    return location, department

# ===============================
# ASSIGN PLAN
# ===============================
def assign_plan_to_user(user, plan):

    assigned_date = timezone.now()
    expiry_date = assigned_date + timedelta(days=plan.duration_days)

    EmployeePlan.objects.update_or_create(
        user=user,
        defaults={
            "plan": plan,
            "assigned_date": assigned_date,
            "expiry_date": expiry_date,
            "status": "active",
        },
    )


# ===============================
# SEND WELCOME EMAIL
# ===============================




# def send_reset_password_email(user, temp_password, reset_link):

#     subject = "Reset Your AgeReboot Healthcare Password"

#     # Plain text version (fallback if HTML not supported)
#     message = f"""
# Hi {user.first_name},

# Welcome to AgeReboot Healthcare.

# Your account has been successfully created.

# Login Details:
# Username: {user.username}
# Temporary Password: {temp_password}

# Please reset your password using the link below:
# {reset_link}

# This link expires in 24 hours.

# Stay healthy,
# AgeReboot Team
# """

#     # HTML email with Reset button
#     html_message = f"""
# <html>
# <body style="font-family: Arial, sans-serif; line-height:1.6; color:#333;">

# <div style="max-width:600px; margin:auto; padding:20px; border:1px solid #eee; border-radius:8px;">

# <h2 style="color:#28a745;">Welcome to AgeReboot Healthcare</h2>

# <p>Hi <strong>{user.first_name}</strong>,</p>

# <p>Your account has been successfully created.</p>

# <div style="background:#f8f9fa; padding:15px; border-radius:5px;">
# <p><strong>Login Details:</strong></p>
# <p>
# Username: {user.username}<br>
# Temporary Password: {temp_password}
# </p>
# </div>

# <p style="margin-top:20px;">
# For security reasons, please reset your password using the button below:
# </p>

# <div style="text-align:center; margin:30px 0;">
# <a href="{reset_link}"
# style="
# display:inline-block;
# padding:14px 28px;
# background-color:#28a745;
# color:white;
# text-decoration:none;
# border-radius:6px;
# font-size:16px;
# font-weight:bold;">
# Reset Password
# </a>
# </div>

# <p>This link expires in <strong>24 hours</strong>.</p>

# <p>
# If you did not expect this email, please ignore it.
# </p>

# <hr>

# <p>
# Stay healthy,<br>
# <strong>AgeReboot Team</strong>
# </p>

# </div>
# </body>
# </html>
# """

#     send_mail(
#         subject=subject,
#         message=message,
#         from_email="kavyasetava135@gmail.com",
#         recipient_list=[user.email],
#         html_message=html_message,
#         fail_silently=False,
#     )


from django.core.mail import send_mail

def send_reset_password_email(user, temp_password=None, reset_link=None):

    subject = "Reset Your AgeReboot Healthcare Password"

    # show login details only if temp password exists
    if temp_password:
        login_details_text = f"""
Login Details:
Username: {user.username}
Temporary Password: {temp_password}
"""
        login_details_html = f"""
<div style="background:#f8f9fa; padding:15px; border-radius:5px;">
<p><strong>Login Details:</strong></p>
<p>
Username: {user.username}<br>
Temporary Password: {temp_password}
</p>
</div>
"""
        account_message = "Your account has been successfully created."
    else:
        login_details_text = ""
        login_details_html = ""
        account_message = "We received a request to reset your password."

    # Plain text version
    message = f"""
Hi {user.first_name},

{account_message}

{login_details_text}

Please reset your password using the link below:
{reset_link}

This link expires in 24 hours.

Stay healthy,
AgeReboot Team
"""

    # HTML email
    html_message = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height:1.6; color:#333;">

<div style="max-width:600px; margin:auto; padding:20px; border:1px solid #eee; border-radius:8px;">

<h2 style="color:#28a745;">AgeReboot Healthcare</h2>

<p>Hi <strong>{user.first_name}</strong>,</p>

<p>{account_message}</p>

{login_details_html}

<p style="margin-top:20px;">
For security reasons, please reset your password using the button below:
</p>

<div style="text-align:center; margin:30px 0;">
<a href="{reset_link}"
style="
display:inline-block;
padding:14px 28px;
background-color:#28a745;
color:white;
text-decoration:none;
border-radius:6px;
font-size:16px;
font-weight:bold;">
Reset Password
</a>
</div>

<p>This link expires in <strong>24 hours</strong>.</p>

<hr>

<p>
Stay healthy,<br>
<strong>AgeReboot Team</strong>
</p>

</div>
</body>
</html>
"""

    send_mail(
        subject=subject,
        message=message,
        from_email="kavyasetava135@gmail.com",
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
