from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status,generics
from django.contrib.auth.models import User
from .serializers import (RegisterSerializer, LoginSerializer,QuestionSerializer,
UserAnswerSerializer,ExcelUploadSerializer,
RoleSerializer,
    CompanySerializer,
    LocationSerializer,
    DepartmentSerializer,
    PlanSerializer,
    UserProfileSerializer, UserProfileUpdateSerializer,
    QuestionSerializer, QuestionWriteSerializer,
    QuestionOptionSerializer,BiomarkerDefinitionSerializer, BiomarkerResultSerializer,
    BulkBiomarkerIngestSerializer, ManualEntrySerializer,
    ManualEntryCreateSerializer, ValidateEntrySerializer,
    CognitiveTemplateSerializer, CognitiveResultSerializer,
    CognitiveSubmitSerializer, WearableDeviceSerializer,
    WearableConnectionSerializer, WearableSyncSerializer,
    LabUploadSerializer, LabTextUploadSerializer,
    ReportRepositorySerializer, ReportUploadSerializer,
    CompareSerializer,)
from allauth.socialaccount.models import SocialAccount
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated,IsAdminUser
from .utils import generate_otp, send_otp_email, otp_expiry_time
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .models import (UserProfile,Question,UserAnswer,Role,Location,
 Department, Plan, EmployeePlan,Challenge,
 ChallengeParticipant,Company,QuestionOption,CreditTransaction,BiomarkerDefinition, BiomarkerResult, ManualEntry,
    BiomarkerCorrelation, WearableDevice, WearableConnection,
    CognitiveAssessmentTemplate, CognitiveAssessmentResult,
    ReportRepository, PillarConfig,)
import pandas as pd
from datetime import timedelta
from .helpers import (
    generate_username,
    generate_temp_password,
    get_location_department,
    assign_plan_to_user,
    send_reset_password_email,
)
from .utils import generate_reset_token
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from .utils import is_token_valid, clear_reset_token
from django.db.models import Count, Q, Avg
from django.shortcuts import get_object_or_404
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
import re
import uuid
import random
from datetime import datetime, timezone

from django.db.models import Q
from django.utils import timezone as dj_timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response






def google_callback(request):
    if request.user.is_authenticated:
        refresh = RefreshToken.for_user(request.user)
        print('refresh',refresh)
        print('refresh.access_token',refresh.access_token)

        # redirect to frontend with JWT
        frontend_url = (
            "http://localhost:5173/auth/callback"
            f"?access={str(refresh.access_token)}"
            f"&refresh={str(refresh)}"
        )

        return redirect(frontend_url)

    return redirect("http://localhost:3000/login?error=google_auth_failed")



@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        otp = generate_otp()
        profile = user.profile
        profile.email_otp = otp
        profile.otp_expires_at = otp_expiry_time()
        profile.is_email_verified = False
        profile.save()

        send_otp_email(user, otp)

        return Response({
            "success": True,
            "message": "Registration successful. OTP sent to email.",
            "statuscode": 201,
             "data": {
                "id": user.id,                # ✅ User ID
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": profile.phone_number  
            }
        }, status=status.HTTP_201_CREATED)

    return Response({
        "success": False,
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)



@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email_otp(request):
    email = request.data.get("email")
    otp = request.data.get("otp")

    if not email or not otp:
        return Response(
            {"message": "Email and OTP are required"},
            status=400
        )

    try:
        user = User.objects.get(email=email)
        profile = user.profile
    except User.DoesNotExist:
        return Response({"message": "Invalid email"}, status=400)

    if profile.is_email_verified:
        return Response(
            {"message": "Email already verified"},
            status=400
        )

    if not profile.email_otp or profile.email_otp != otp:
        return Response(
            {"message": "Invalid OTP"},
            status=400
        )

    if timezone.now() > profile.otp_expires_at:
        return Response(
            {"message": "OTP expired"},
            status=400
        )

    # ✅ SUCCESS → CLEAR OTP ALWAYS
    profile.is_email_verified = True
    profile.email_otp = ""           # ← cleared
    profile.otp_expires_at = None    # ← cleared
    profile.save(update_fields=[
        "is_email_verified",
        "email_otp",
        "otp_expires_at"
    ])

    return Response({
        "success": True,
        "message": "Email verified successfully"
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def resend_email_otp(request):
    email = request.data.get("email")

    try:
        user = User.objects.get(email=email)
        profile = user.profile
    except User.DoesNotExist:
        return Response({"message": "Invalid email"}, status=400)

    if profile.is_email_verified:
        return Response(
            {"message": "Email already verified"},
            status=400
        )

    otp = generate_otp()

    profile.email_otp = otp           # ← old OTP replaced
    profile.otp_expires_at = otp_expiry_time()
    profile.save(update_fields=[
        "email_otp",
        "otp_expires_at"
    ])

    send_otp_email(user, otp)

    return Response({
        "success": True,
        "message": "New OTP sent to email"
    })



@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.validated_data["user"]
    refresh = RefreshToken.for_user(user)

    profile = user.profile  
    return Response({
        "success": True,
        "message": "Login successful",
        "data": {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role_id": profile.role.id if profile.role else None,
            "role": profile.role.name if profile.role else None,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def send_phone_otp(request):
    phone_number = request.data.get("phone_number")

    if not phone_number:
        return Response(
            {"message": "Phone number is required"},
            status=400
        )

    profile = UserProfile.objects.filter(phone_number=phone_number).first()
    if not profile:
        return Response(
            {"message": "Phone number not registered"},
            status=400
        )

    otp = generate_otp()
    profile.phone_otp = otp
    profile.phone_otp_expires_at = otp_expiry_time()
    profile.save(update_fields=[
        "phone_otp",
        "phone_otp_expires_at"
    ])

    # 🔴 Integrate SMS gateway here
    print("PHONE OTP:", otp)

    return Response({
        "success": True,
        "message": "OTP sent to phone number"
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_phone_otp(request):
    phone_number = request.data.get("phone_number")
    otp = request.data.get("otp")

    if not phone_number or not otp:
        return Response(
            {"message": "Phone number and OTP are required"},
            status=400
        )

    profile = UserProfile.objects.filter(phone_number=phone_number).first()
    if not profile:
        return Response(
            {"message": "Invalid phone number"},
            status=400
        )

    if profile.phone_otp != otp:
        return Response(
            {"message": "Invalid OTP"},
            status=400
        )

    if timezone.now() > profile.phone_otp_expires_at:
        return Response(
            {"message": "OTP expired"},
            status=400
        )

    # ✅ SUCCESS
    profile.is_phone_verified = True
    profile.phone_otp = None
    profile.phone_otp_expires_at = None
    profile.save(update_fields=[
        "is_phone_verified",
        "phone_otp",
        "phone_otp_expires_at"
    ])

    user = profile.user
    refresh = RefreshToken.for_user(user)

    return Response({
        "success": True,
        "message": "Phone login successful",
        "data": {
            "user_id": user.id,
            "phone_number": profile.phone_number,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def resend_phone_otp(request):
    phone_number = request.data.get("phone_number")

    profile = UserProfile.objects.filter(phone_number=phone_number).first()
    if not profile:
        return Response({"message": "Invalid phone number"}, status=400)

    if profile.is_phone_verified:
        return Response({"message": "Phone already verified"}, status=400)

    otp = generate_otp()
    profile.phone_otp = otp
    profile.phone_otp_expires_at = otp_expiry_time()
    profile.save(update_fields=[
        "phone_otp",
        "phone_otp_expires_at"
    ])

    print("RESEND PHONE OTP:", otp)

    return Response({
        "success": True,
        "message": "New OTP sent to phone"
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_questions(request):
    questions = Question.objects.all().order_by("order", "id")
    serializer = QuestionSerializer(questions, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_answers(request):
    user = request.user
    answers = request.data  # list of answers
    print('answers',answers)

    for answer in answers:
        serializer = UserAnswerSerializer(data=answer)
        serializer.is_valid(raise_exception=True)

        UserAnswer.objects.update_or_create(
            user=user,
            question=serializer.validated_data["question"],
            defaults=serializer.validated_data,
        )

    return Response({"message": "Answers saved successfully"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_answers(request):
    answers = UserAnswer.objects.filter(user=request.user)
    serializer = UserAnswerSerializer(answers, many=True)
    return Response(serializer.data)



COMMON_EMAIL_TYPOS = {
    "gmai.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmal.com": "gmail.com",
    "hotmial.com": "hotmail.com",
    "yahho.com": "yahoo.com",
}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_employee_upload(request):

    REQUIRED_HEADERS = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "location",
        "department",
        "plan",
    ]

    serializer = ExcelUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    file = serializer.validated_data["file"]

    try:
        df = pd.read_excel(file)
    except Exception:
        return Response({"error": "Invalid Excel file"}, status=400)

    if list(df.columns) != REQUIRED_HEADERS:
        return Response(
            {"error": "Invalid file format", "expected": REQUIRED_HEADERS},
            status=400,
        )

    hr_profile = request.user.profile
    company = hr_profile.company
    if not company:
        return Response({"error": "HR has no company assigned"}, status=400)

    df = df.dropna(how="all")

    # ----------------------------------
    # 🚀 PREFETCH / CACHE (SPEED BOOST)
    # ----------------------------------
    employee_role = Role.objects.get(name="employee")

    existing_users = {
        u.email.lower(): u
        for u in User.objects.filter(email__in=df["email"].dropna().tolist())
    }

    plans_cache = {
        p.name.lower(): p
        for p in Plan.objects.all()
    }

    created_users = []
    updated_users = []
    validation_errors = []
    db_errors = []
    email_errors = []

    for index, row in df.iterrows():
        try:
            first_name = str(row["first_name"]).strip()
            last_name = str(row["last_name"]).strip()
            email = str(row["email"]).strip().lower()
            phone = str(row["phone_number"]).strip()
            location_name = str(row["location"]).strip()
            department_name = str(row["department"]).strip()
            plan_name = str(row["plan"]).strip().lower()

            # -----------------------------
            # EMAIL VALIDATION
            # -----------------------------
            if not email:
                validation_errors.append({
                    "row": index + 2,
                    "error": "Email is empty"
                })
                continue

            try:
                validate_email(email)
            except ValidationError:
                validation_errors.append({
                    "row": index + 2,
                    "email": email,
                    "error": "Invalid email format"
                })
                continue

            domain = email.split("@")[-1]
            if domain in COMMON_EMAIL_TYPOS:
                validation_errors.append({
                    "row": index + 2,
                    "email": email,
                    "error": f"Possible typo. Did you mean {COMMON_EMAIL_TYPOS[domain]}?"
                })
                continue

            # -----------------------------
            # CREATE OR UPDATE USER
            # -----------------------------
            user = existing_users.get(email)
            is_new_user = False

            if user:
                # UPDATE
                user.first_name = first_name
                user.last_name = last_name
                user.save(update_fields=["first_name", "last_name"])
                updated_users.append(user.username)
            else:
                # CREATE
                username = generate_username(first_name, last_name)
                temp_password = generate_temp_password()

                user = User.objects.create(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.set_password(temp_password)
                user.save()

                existing_users[email] = user
                created_users.append(username)

            # -----------------------------
            # LOCATION & DEPARTMENT
            # -----------------------------
            location, department = get_location_department(
                company, location_name, department_name
            )

            # -----------------------------
            # PROFILE UPSERT
            # -----------------------------
            profile = user.profile
            profile.phone_number = phone
            profile.company = company
            profile.role = employee_role
            profile.location = location
            profile.department = department
            profile.is_email_verified = True
            profile.invite_status = "invited"
            profile.save()

            # -----------------------------
            # PLAN ASSIGNMENT (CACHED)
            # -----------------------------
            if plan_name:
                plan = plans_cache.get(plan_name)
                if plan:
                    assign_plan_to_user(user, plan)
                else:
                    validation_errors.append({
                        "row": index + 2,
                        "email": email,
                        "error": "Plan does not exist"
                    })

            # -----------------------------
            # EMAIL ONLY FOR NEW USERS
            # -----------------------------
            if is_new_user:
                try:
                    token = generate_reset_token(user)
                    # reset_link = f"http://localhost:3000/reset-password/{token}"
                    reset_link = f"http://localhost:3000/forgot-password/{token}"
                    send_reset_password_email(user, temp_password, reset_link)
                except Exception as e:
                    email_errors.append({
                        "row": index + 2,
                        "email": email,
                        "error": "Email sending failed",
                        "details": str(e)
                    })

        except Exception as e:
            db_errors.append({
                "row": index + 2,
                "email": email if email else None,
                "error": str(e)
            })

    return Response(
        {
            "summary": {
                "total_rows": len(df),
                "created": len(created_users),
                "updated": len(updated_users),
                "failed": len(validation_errors) + len(db_errors) + len(email_errors),
            },
            "created_users": created_users,
            "updated_users": updated_users,
            "validation_errors": validation_errors,
            "db_errors": db_errors,
            "email_errors": email_errors,
        },
        status=207,  
    )


# ==========================================
# DOWNLOAD TEMPLATE
# ==========================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_employee_template(request):

    headers = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "location",
        "department",
        "plan",
    ]

    df = pd.DataFrame(columns=headers)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=employee_template.xlsx"

    df.to_excel(response, index=False)
    return response





@api_view(["POST"])
def invite_employee(request):

    email = request.data.get("email")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    token = generate_reset_token(user)

    send_reset_password_email(user, token)

    profile = user.profile
    profile.invite_status = "invited"
    profile.save()

    return Response({"message": "Invitation sent"})




# @api_view(["POST"])
# def reset_password(request):

#     token = request.data.get("token")
#     new_password = request.data.get("password")

#     if not token or not new_password:
#         return Response(
#             {"error": "Token and password required"},
#             status=400
#         )

#     try:
#         user = UserProfile.objects.get(reset_token=token)
#     except UserProfile.DoesNotExist:
#         return Response({"error": "Invalid token"}, status=400)

#     if not is_token_valid(user, token):
#         return Response({"error": "Token expired"}, status=400)

#     user.password = make_password(new_password)
#     user.status = "active"

#     clear_reset_token(user)

#     user.save()

#     return Response({
#         "message": "Password reset successful",
#         "status": "active"
#     })

@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):

    token = request.data.get("token")
    new_password = request.data.get("password")

    if not token or not new_password:
        return Response(
            {"error": "Token and password required"},
            status=400
        )

    try:
        profile = UserProfile.objects.get(reset_token=token)
    except UserProfile.DoesNotExist:
        return Response({"error": "Invalid token"}, status=400)

    # validate token expiry
    if not is_token_valid(profile, token):
        return Response({"error": "Token expired"}, status=400)

    # ✅ UPDATE PASSWORD IN USER MODEL
    user = profile.user
    user.set_password(new_password)
    user.save()

    # ✅ UPDATE PROFILE STATUS
    profile.invite_status = "active"
    profile.password_reset_required = False
    profile.is_email_verified = True

    clear_reset_token(profile)
    profile.save()

    return Response({
        "message": "Password reset successful",
        "status": "active"
    })



@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):

    email = request.data.get("email")
    username = request.data.get("username")

    # at least one required
    if not email and not username:
        return Response(
            {"error": "Email or username required"},
            status=400
        )

    try:
        # find user by email or username
        if email:
            user = User.objects.get(email=email)
        else:
            user = User.objects.get(username=username)

    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # ✅ generate reset token (your function)
    token = generate_reset_token(user)

    # create reset link
    reset_link = f"http://localhost:3000/reset-password/{token}"

    # send email (use your email function)
    send_reset_password_email(user, None, reset_link)

    return Response({
        "message": "Password reset link sent to registered email"
    })


 


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employees_list_api(request):

    company = request.user.profile.company
    if not company:
        return Response({"error": "No company assigned"}, status=400)

    allowed_keys = {"department_id", "location_id", "status"}
    wrong_keys = set(request.GET.keys()) - allowed_keys

    if wrong_keys:
        return Response(
            {
                "error": "Invalid query parameter(s)",
                "allowed_params": list(allowed_keys),
                "received_invalid": list(wrong_keys),
            },
            status=400,
        )

  
    department_id = request.GET.get("department_id")
    location_id = request.GET.get("location_id")
    status_filter = request.GET.get("status")


    if department_id and not department_id.isdigit():
        return Response(
            {"error": "department_id must be a number"},
            status=400,
        )

    if location_id and not location_id.isdigit():
        return Response(
            {"error": "location_id must be a number"},
            status=400,
        )

    
    profiles_qs = (
        UserProfile.objects
        .select_related("user", "department", "location", "role")
        .filter(company=company, role__name="employee")
    )

    
    if department_id:
        profiles_qs = profiles_qs.filter(department_id=int(department_id))

    if location_id:
        profiles_qs = profiles_qs.filter(location_id=int(location_id))

    if status_filter:
        profiles_qs = profiles_qs.filter(invite_status=status_filter)

   
    profiles_qs = profiles_qs.prefetch_related("user__employeeplan_set")
    print('profiles_qs',profiles_qs)

   
    employees_data = []

    for profile in profiles_qs:
        active_plans = [
            ep.plan.name
            for ep in profile.user.employeeplan_set.all()
            if ep.status == "active"
        ]

        employees_data.append({
            "user_id": profile.user.id,
            "employee_name": f"{profile.user.first_name} {profile.user.last_name}".strip(),
            "email": profile.user.email,
            "phone_number": profile.phone_number,
            "department": {
                "id": profile.department.id,
                "name": profile.department.name,
            } if profile.department else None,
            "location": {
                "id": profile.location.id,
                "name": profile.location.name,
            } if profile.location else None,
            "plans": active_plans,
            "status": profile.invite_status,
        })

    
    all_profiles = UserProfile.objects.filter(
        company=company,
        role__name="employee"
    )

    total_emp_count = all_profiles.count()

    status_counts_qs = (
        all_profiles
        .values("invite_status")
        .annotate(count=Count("id"))
    )

    status_map = {
        "active": 0,
        "Registered": 0,
        "inactive": 0,
        "invited": 0,
    }

    for item in status_counts_qs:
        if item["invite_status"] in status_map:
            status_map[item["invite_status"]] = item["count"]

    plan_counts_qs = (
        EmployeePlan.objects
        .filter(
            user__profile__company=company,
            user__profile__role__name="employee",
            status="active"
        )
        .values("plan__name")
        .annotate(count=Count("id"))
    )

    plan_counts = {"basic": 0, "premium": 0, "gold": 0}

    for item in plan_counts_qs:
        plan_counts[item["plan__name"]] = item["count"]

    
    return Response({
        "summary": {
            "total_emp_count": total_emp_count,
            "active_count": status_map["active"],
            "registered_count": status_map["Registered"],
            "inactive_count": status_map["inactive"],
            "invited_count": status_map["invited"],
            "plan_counts": plan_counts,
        },
        "employees": employees_data,
    })




@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def employee_edit_api(request, user_id):

    company = request.user.profile.company
    if not company:
        return Response({"error": "No company assigned"}, status=400)

    try:
        user = User.objects.select_related("profile").get(
            id=user_id,
            profile__company=company,
            profile__role__name="employee"
        )
    except User.DoesNotExist:
        return Response({"error": "Employee not found"}, status=404)

    data = request.data
    profile = user.profile

    
    user.first_name = data.get("first_name", user.first_name)
    user.last_name = data.get("last_name", user.last_name)
    user.save(update_fields=["first_name", "last_name"])

    
    if "phone_number" in data:
        profile.phone_number = data["phone_number"]

    if "invite_status" in data:
        profile.invite_status = data["invite_status"]

   
    if "department" in data:
        department = Department.objects.filter(
            company=company,
            name__iexact=data["department"]
        ).first()

        if not department:
            return Response(
                {"error": "Invalid department"},
                status=400
            )

        profile.department = department

    
    if "location" in data:
        location = Location.objects.filter(
            company=company,
            name__iexact=data["location"]
        ).first()

        if not location:
            return Response(
                {"error": "Invalid location"},
                status=400
            )

        profile.location = location

    profile.save()

   
    if "plan" in data:
        plan = Plan.objects.filter(
            name__iexact=data["plan"]
        ).first()

        if not plan:
            return Response(
                {"error": "Invalid plan"},
                status=400
            )

        # expire existing active plans
        EmployeePlan.objects.filter(
            user=user,
            status="active"
        ).update(status="expired")

        # assign new plan
        EmployeePlan.objects.create(
            user=user,
            plan=plan,
            assigned_date=timezone.now(),
            expiry_date=timezone.now() + timezone.timedelta(days=plan.duration_days),
            status="active"
        )

   
    return Response({
        "message": "Employee updated successfully",
        "employee": {
            "id": user.id,
            "employee_name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "phone_number": profile.phone_number,
            "department": profile.department.name if profile.department else None,
            "location": profile.location.name if profile.location else None,
            "status": profile.invite_status,
            "plans": list(
                EmployeePlan.objects.filter(
                    user=user, status="active"
                ).values_list("plan__name", flat=True)
            ),
        }
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def location_dropdown_api(request):

    company = request.user.profile.company
    if not company:
        return Response({"error": "No company assigned"}, status=400)

    locations = Location.objects.filter(company=company).values("id", "name")

    return Response({
        "locations": list(locations)
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def department_dropdown_api(request):

    company = request.user.profile.company
    if not company:
        return Response({"error": "No company assigned"}, status=400)

    departments = Department.objects.filter(company=company).values("id", "name")

    return Response({
        "departments": list(departments)
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def status_dropdown_api(request):

    return Response({
        "statuses": [
            {"key": key, "label": label}
            for key, label in UserProfile.INVITE_STATUS
        ]
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_challenge(request):
    profile = request.user.profile

    if profile.role.name != "hr_admin":
        return Response({"error": "Only HR can create challenges"}, status=403)

    data = request.data

    challenge = Challenge.objects.create(
        company=profile.company,
        created_by=request.user,
        name=data["name"],
        reward=data["reward"],
        rules=data["rules"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        challenge_type=data["challenge_type"],
        status="active"
    )

    challenge.departments.set(
        Department.objects.filter(id__in=data.get("department_ids", []))
    )
    challenge.locations.set(
        Location.objects.filter(id__in=data.get("location_ids", []))
    )

    return Response({
        "message": "Challenge created successfully",
        "challenge_id": challenge.id
    }, status=201)


# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def hr_challenges_list(request):
#     profile = request.user.profile
#     print('profile',profile)

#     qs = Challenge.objects.filter(company=profile.company)

#     status_filter = request.GET.get("status")
#     if status_filter:
#         qs = qs.filter(status=status_filter)

#     data = []
#     for ch in qs:
#         participant_count = ChallengeParticipant.objects.filter(challenge=ch).count()
#         remaining_days = (ch.end_date - timezone.now().date()).days

#         data.append({
#             "id": ch.id,
#             "name": ch.name,
#             "reward": ch.reward,
#             "participants": participant_count,
#             "days_remaining": max(remaining_days, 0),
#             "status": ch.status
#         })

#     return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def hr_challenges_list(request):
    profile = request.user.profile

    
    qs = (
        Challenge.objects
        .filter(company=profile.company)
        .select_related("created_by")
        .prefetch_related("departments", "locations")
        .annotate(
            participants_count=Count("challengeparticipant", distinct=True),
            avg_progress=Avg("challengeparticipant__progress"),
        )
    )

    
    status_filter = request.GET.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)

    today = timezone.now().date()
    data = []

    for ch in qs:
        remaining_days = (ch.end_date - today).days

        data.append({
            "id": ch.id,
            "name": ch.name,
            "reward": ch.reward,

            # 👥 Participants
            "participants": ch.participants_count,

            # 📊 Progress bar (0–100)
            "average_progress": int(ch.avg_progress or 0),

            # ⏳ Days remaining
            "days_remaining": max(remaining_days, 0),

            # 🏷 Departments
            "departments": [
                dept.name for dept in ch.departments.all()
            ],

            # 🧑 Created info
            "created_at": ch.created_at.strftime("%d %b"),
            "created_by": ch.created_by.first_name if ch.created_by else None,

            # 🔖 Status
            "status": ch.status,
        })

    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employee_challenges(request):
    profile = request.user.profile

    qs = Challenge.objects.filter(
        company=profile.company,
        status="active"
    ).filter(
        Q(departments=profile.department) | Q(departments=None),
        Q(locations=profile.location) | Q(locations=None)
    ).distinct()

    return Response([
        {
            "id": ch.id,
            "name": ch.name,
            "reward": ch.reward,
            "end_date": ch.end_date
        }
        for ch in qs
    ])

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_challenge(request, id):
    challenge = get_object_or_404(Challenge, id=id, status="active")

    obj, created = ChallengeParticipant.objects.get_or_create(
        challenge=challenge,
        user=request.user
    )

    if not created:
        return Response({"message": "Already joined"})

    return Response({"message": "Joined challenge successfully"})

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_progress(request, id):

    participant = get_object_or_404(
        ChallengeParticipant,
        challenge_id=id,
        user=request.user
    )

    # 🔴 STRICT KEY CHECK
    if "progress" not in request.data:
        return Response(
            {"error": "progress field is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 🔴 TYPE VALIDATION
    try:
        progress = int(request.data["progress"])
    except (ValueError, TypeError):
        return Response(
            {"error": "progress must be a number"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 🔴 RANGE VALIDATION
    if progress < 0 or progress > 100:
        return Response(
            {"error": "progress must be between 0 and 100"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ✅ UPDATE PROGRESS
    participant.progress = progress

    if progress >= 100:
        participant.status = "completed"
        participant.completed_at = timezone.now()
    else:
        participant.status = "inprogress"
        participant.completed_at = None

    participant.save()

    return Response(
        {
            "message": "Progress updated",
            "progress": participant.progress,
            "status": participant.status,
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def challenge_participants(request, id):
    qs = ChallengeParticipant.objects.filter(challenge_id=id)

    return Response([
        {
            "employee": p.user.username,
            "progress": p.progress,
            "status": p.status
        }
        for p in qs
    ])




# ══════════════════════════════════════════════
# ROLE
# ══════════════════════════════════════════════

class RoleListCreateView(generics.ListCreateAPIView):
    """
    GET  /admin/roles/      → list all roles
    POST /admin/roles/      → create a role
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]


class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /admin/roles/<id>/  → retrieve role
    PUT    /admin/roles/<id>/  → full update
    PATCH  /admin/roles/<id>/  → partial update
    DELETE /admin/roles/<id>/  → delete
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]


# ══════════════════════════════════════════════
# COMPANY
# ══════════════════════════════════════════════

class CompanyListCreateView(generics.ListCreateAPIView):
    """
    GET  /admin/companies/   → list all companies
    POST /admin/companies/   → create a company
    """
    queryset = Company.objects.all().order_by("-created_at")
    serializer_class = CompanySerializer
    permission_classes = [IsAdminUser]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["name"]
    filterset_fields = ["status"]
    ordering_fields = ["name", "created_at"]


class CompanyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /admin/companies/<id>/
    PUT    /admin/companies/<id>/
    PATCH  /admin/companies/<id>/
    DELETE /admin/companies/<id>/
    """
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAdminUser]


# ══════════════════════════════════════════════
# LOCATION
# ══════════════════════════════════════════════

class LocationListCreateView(generics.ListCreateAPIView):
    """
    GET  /admin/locations/        → list all locations (filter by ?company=<id>)
    POST /admin/locations/        → create a location
    """
    queryset = Location.objects.select_related("company").all()
    serializer_class = LocationSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ["name", "company__name"]
    filterset_fields = ["company"]


class LocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /admin/locations/<id>/
    PUT    /admin/locations/<id>/
    PATCH  /admin/locations/<id>/
    DELETE /admin/locations/<id>/
    """
    queryset = Location.objects.select_related("company").all()
    serializer_class = LocationSerializer
    permission_classes = [IsAdminUser]


# ══════════════════════════════════════════════
# DEPARTMENT
# ══════════════════════════════════════════════

class DepartmentListCreateView(generics.ListCreateAPIView):
    """
    GET  /admin/departments/      → list (filter by ?company=<id>)
    POST /admin/departments/      → create
    """
    queryset = Department.objects.select_related("company").all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ["name", "company__name"]
    filterset_fields = ["company"]


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /admin/departments/<id>/
    PUT    /admin/departments/<id>/
    PATCH  /admin/departments/<id>/
    DELETE /admin/departments/<id>/
    """
    queryset = Department.objects.select_related("company").all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminUser]


# ══════════════════════════════════════════════
# PLAN
# ══════════════════════════════════════════════

class PlanListCreateView(generics.ListCreateAPIView):
    """
    GET  /admin/plans/
    POST /admin/plans/
    """
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [SearchFilter]
    search_fields = ["name"]


class PlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /admin/plans/<id>/
    PUT    /admin/plans/<id>/
    PATCH  /admin/plans/<id>/
    DELETE /admin/plans/<id>/
    """
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsAdminUser]


# ══════════════════════════════════════════════
# USER PROFILE
# ══════════════════════════════════════════════

class UserProfileListView(generics.ListAPIView):
    """
    GET /admin/user-profiles/
    Supports filters: ?company=<id> &role=<id> &invite_status=active &department=<id> &location=<id>
    Supports search:  ?search=<name/email>
    """
    queryset = UserProfile.objects.select_related(
        "user", "company", "role", "location", "department"
    ).all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    search_fields = ["user__username", "user__email", "user__first_name", "user__last_name"]
    filterset_fields = ["company", "role", "department", "location", "invite_status"]
    ordering_fields = ["user__username", "user__email"]


class UserProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /admin/user-profiles/<id>/   → retrieve profile
    PATCH  /admin/user-profiles/<id>/   → partial update (role, company, dept, location …)
    DELETE /admin/user-profiles/<id>/   → delete profile (and cascade to User)
    """
    queryset = UserProfile.objects.select_related(
        "user", "company", "role", "location", "department"
    ).all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    def destroy(self, request, *args, **kwargs):
        profile = self.get_object()
        user = profile.user
        user.delete()          # cascades → deletes profile too
        return Response(
            {"detail": "User and profile deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


# ══════════════════════════════════════════════
# QUESTION
# ══════════════════════════════════════════════

class QuestionListCreateView(generics.ListCreateAPIView):
    """
    GET  /admin/questions/        → list all questions (with nested options)
    POST /admin/questions/        → create a question
    """
    queryset = Question.objects.prefetch_related("options").all().order_by("order")
    permission_classes = [IsAdminUser]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ["text"]
    filterset_fields = ["question_type", "is_required"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return QuestionWriteSerializer
        return QuestionSerializer


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /admin/questions/<id>/
    PUT    /admin/questions/<id>/
    PATCH  /admin/questions/<id>/
    DELETE /admin/questions/<id>/
    """
    queryset = Question.objects.prefetch_related("options").all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return QuestionWriteSerializer
        return QuestionSerializer


# ══════════════════════════════════════════════
# QUESTION OPTION
# ══════════════════════════════════════════════

class QuestionOptionListCreateView(generics.ListCreateAPIView):
    """
    GET  /admin/question-options/          → list all options (filter by ?question=<id>)
    POST /admin/question-options/          → create an option
    """
    queryset = QuestionOption.objects.select_related("question").all()
    serializer_class = QuestionOptionSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["question"]
    search_fields = ["label"]


class QuestionOptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /admin/question-options/<id>/
    PUT    /admin/question-options/<id>/
    PATCH  /admin/question-options/<id>/
    DELETE /admin/question-options/<id>/
    """
    queryset = QuestionOption.objects.select_related("question").all()
    serializer_class = QuestionOptionSerializer
    permission_classes = [IsAdminUser]



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_credits_mock(request):
    amount = int(request.data.get('amount', 100))
    profile = request.user.profile  # ✅

    profile.credits += amount
    profile.save(update_fields=["credits"])

    CreditTransaction.objects.create(
        user=request.user,
        type="purchase",
        amount=amount,
        description="Credits Purchased"
    )

    return Response({
        "status": "success",
        "new_balance": profile.credits
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_credits(request):
    user = request.user
    profile = user.profile  # ✅ IMPORTANT

    transactions = profile.user.credit_transactions.all().order_by('-created_at')

    return Response({
        "available": profile.credits,
        "transactions": [
            {
                "type": t.type,
                "amount": t.amount,
                "description": t.description,
                "timestamp": t.created_at.isoformat()
            } for t in transactions
        ]
    })
    user = request.user

    transactions = user.credit_transactions.all().order_by('-created_at')[:10]

    return Response({
        "available": user.credits,
        "transactions": [
            {
                "type": t.type,
                "amount": t.amount,
                "description": t.description,
                "timestamp": t.created_at.isoformat()
            } for t in transactions
        ]
    })

"""
biomarkers/views.py

All biomarker-related API views.  Each endpoint mirrors the FastAPI
routes in the original spec, but everything is driven from the DB
rather than hard-coded dicts.
"""



# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _biomarker_status(value, defn: BiomarkerDefinition):
    """Return 'green' | 'yellow' | 'red' for a given value."""
    lo, hi = defn.optimal_low or 0, defn.optimal_high or 100
    d = defn.direction
    if d == "lower_better":
        return "green" if value <= hi else ("yellow" if value <= hi * 1.3 else "red")
    if d == "higher_better":
        return "green" if value >= lo else ("yellow" if value >= lo * 0.7 else "red")
    # optimal_range
    return "green" if lo <= value <= hi else ("yellow" if lo * 0.8 <= value <= hi * 1.2 else "red")


def _is_red(value, defn: BiomarkerDefinition):
    lo, hi = defn.optimal_low or 0, defn.optimal_high or 100
    d = defn.direction
    if d == "lower_better":  return value > hi * 1.3
    if d == "higher_better": return value < lo * 0.7
    return value < lo * 0.8 or value > hi * 1.2


def _ingest_bulk(user, biomarkers_data):
    """
    Core ingest helper.  `biomarkers_data` is a list of dicts:
      [{biomarker_code, value, source, collected_at (opt)}, ...]
    Returns list of saved BiomarkerResult instances.
    """
    results = []
    codes   = {b["biomarker_code"] for b in biomarkers_data}
    defns   = {d.code: d for d in BiomarkerDefinition.objects.filter(code__in=codes)}

    for bm in biomarkers_data:
        defn = defns.get(bm["biomarker_code"])
        if not defn:
            continue
        collected = bm.get("collected_at") or dj_timezone.now()
        obj = BiomarkerResult.objects.create(
            user=user,
            biomarker=defn,
            value=bm["value"],
            source=bm.get("source", "MANUAL"),
            collected_at=collected,
        )
        results.append(obj)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Bulk ingest
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ingest_biomarkers(request):
    """POST /biomarkers/ingest"""
    ser = BulkBiomarkerIngestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    saved = _ingest_bulk(request.user, ser.validated_data["biomarkers"])
    return Response({
        "ingested": len(saved),
        "results":  BiomarkerResultSerializer(saved, many=True).data,
    }, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Definitions
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
def get_biomarker_definitions(request):
    """GET /biomarkers/definitions/all  – public, no auth required"""
    defs = BiomarkerDefinition.objects.all()
    return Response({"definitions": BiomarkerDefinitionSerializer(defs, many=True).data})


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Compare two biomarkers
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def compare_biomarkers(request):
    """POST /biomarkers/compare  {code_a, code_b}"""
    ser = CompareSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    code_a, code_b = ser.validated_data["code_a"], ser.validated_data["code_b"]

    try:
        defn_a = BiomarkerDefinition.objects.get(code=code_a)
        defn_b = BiomarkerDefinition.objects.get(code=code_b)
    except BiomarkerDefinition.DoesNotExist:
        return Response({"error": "Invalid biomarker code"}, status=400)

    uid = request.user.id

    def _history(code):
        rows = (BiomarkerResult.objects
                .filter(user_id=uid, biomarker__code=code)
                .order_by("collected_at")[:50])
        return [{"date": r.collected_at.date().isoformat(), "value": r.value} for r in rows]

    # correlation lookup (try both orderings)
    corr = (BiomarkerCorrelation.objects
            .filter(Q(biomarker_a__code=code_a, biomarker_b__code=code_b) |
                    Q(biomarker_a__code=code_b, biomarker_b__code=code_a))
            .first())

    correlation = None
    if corr:
        correlation = {"strength": corr.strength, "direction": corr.direction,
                       "insight": corr.insight}

    def _defn_dict(defn, hist):
        return {"code": defn.code, "name": defn.name, "unit": defn.unit,
                "pillar": defn.pillar, "optimal_low": defn.optimal_low,
                "optimal_high": defn.optimal_high, "direction": defn.direction,
                "history": hist}

    return Response({
        "biomarker_a": _defn_dict(defn_a, _history(code_a)),
        "biomarker_b": _defn_dict(defn_b, _history(code_b)),
        "correlation": correlation,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Pillar dashboard
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pillar_dashboard(request):
    """GET /biomarkers/pillar-dashboard"""
    uid = request.user.id

    all_bms = list(BiomarkerResult.objects
                   .filter(user_id=uid)
                   .select_related("biomarker")
                   .order_by("-collected_at")[:500])

    latest_by_code  = {}
    history_by_code = {}
    for bm in all_bms:
        code = bm.biomarker.code
        if code not in latest_by_code:
            latest_by_code[code] = bm
        if code not in history_by_code:
            history_by_code[code] = []
        if len(history_by_code[code]) < 10:
            history_by_code[code].append(bm)

    pillar_cfgs = {p.code: p for p in PillarConfig.objects.all()}
    pillars     = {}

    for defn in BiomarkerDefinition.objects.select_related().all():
        pillar = defn.pillar
        if pillar not in pillars:
            cfg = pillar_cfgs.get(pillar)
            pillars[pillar] = {
                "code": pillar,
                "name":  cfg.name  if cfg else pillar,
                "color": cfg.color if cfg else "#7B35D8",
                "biomarkers": [], "red": 0, "yellow": 0, "green": 0,
            }

        bm = latest_by_code.get(defn.code)
        if bm:
            s = _biomarker_status(bm.value, defn)
            history = [{"value": round(h.value, 2),
                        "date":  h.collected_at.date().isoformat()}
                       for h in reversed(history_by_code.get(defn.code, []))]
            pillars[pillar]["biomarkers"].append({
                "code": defn.code, "name": defn.name,
                "value": round(bm.value, 2), "unit": defn.unit,
                "domain": defn.domain,
                "optimal_low": defn.optimal_low, "optimal_high": defn.optimal_high,
                "direction": defn.direction, "status": s,
                "history": history, "data_source": defn.data_source,
            })
            pillars[pillar][s] += 1
        else:
            pillars[pillar]["biomarkers"].append({
                "code": defn.code, "name": defn.name,
                "value": None, "unit": defn.unit,
                "domain": defn.domain,
                "optimal_low": defn.optimal_low, "optimal_high": defn.optimal_high,
                "direction": defn.direction, "status": "missing",
                "history": [], "data_source": defn.data_source,
            })

    return Response({"pillars": pillars})


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Predictions
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def biomarker_predictions(request):
    """GET /biomarkers/predictions"""
    from django.db.models import Count
    uid  = request.user.id
    user = request.user

    # Compliance score (mirrored from FastAPI logic)
    med_logs_count         = getattr(user, "medication_logs",      None)
    nutrition_logs_count   = getattr(user, "nutrition_logs",       None)
    daily_challenges_done  = getattr(user, "daily_challenges",     None)
    ml = med_logs_count.count()         if med_logs_count        else 0
    nl = nutrition_logs_count.count()   if nutrition_logs_count  else 0
    dc = daily_challenges_done.filter(completed=True).count() if daily_challenges_done else 0
    compliance_score = min(100, ml * 5 + nl * 3 + dc * 8)

    all_bms = list(BiomarkerResult.objects
                   .filter(user_id=uid)
                   .select_related("biomarker")
                   .order_by("-collected_at")[:500])

    latest_by_code  = {}
    history_by_code = {}
    for bm in all_bms:
        code = bm.biomarker.code
        if code not in latest_by_code:
            latest_by_code[code] = bm
        if code not in history_by_code:
            history_by_code[code] = []
        if len(history_by_code[code]) < 10:
            history_by_code[code].append(bm)

    predictions = []
    cf = compliance_score / 100.0

    for defn in BiomarkerDefinition.objects.all():
        bm = latest_by_code.get(defn.code)
        if not bm or not _is_red(bm.value, defn):
            continue

        val     = bm.value
        history = [h.value for h in history_by_code.get(defn.code, [])]
        trend   = (history[0] - history[-1]) / len(history) if len(history) >= 2 else 0
        lo, hi  = defn.optimal_low or 0, defn.optimal_high or 100
        d       = defn.direction

        if d == "lower_better":
            imp = -abs(trend) * cf * 0.5
            p1, p2, p3 = max(0, val + imp*30), max(0, val + imp*60), max(0, val + imp*90)
        elif d == "higher_better":
            imp = abs(trend) * cf * 0.5
            p1, p2, p3 = val + imp*30, val + imp*60, val + imp*90
        else:
            mid = (lo + hi) / 2
            mv  = (mid - val) * cf * 0.1
            p1, p2, p3 = val + mv, val + mv*2, val + mv*3

        hist_data = [{"value": round(h.value, 2),
                      "date":  h.collected_at.date().isoformat()}
                     for h in reversed(history_by_code.get(defn.code, []))]

        predictions.append({
            "code": defn.code, "name": defn.name,
            "unit": defn.unit, "current": round(val, 2),
            "optimal_low": lo, "optimal_high": hi, "direction": d,
            "predictions": [
                {"month": 1, "value": round(p1, 2)},
                {"month": 2, "value": round(p2, 2)},
                {"month": 3, "value": round(p3, 2)},
            ],
            "compliance_score": compliance_score,
            "history": hist_data,
        })

    return Response({"predictions": predictions, "compliance_score": compliance_score})


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Cognitive assessments
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_cognitive_assessments(request):
    """GET /biomarkers/cognitive-assessments"""
    templates = CognitiveAssessmentTemplate.objects.all()
    completed = CognitiveAssessmentResult.objects.filter(
        user=request.user).select_related("template").order_by("-completed_at")[:50]

    return Response({
        "assessments": CognitiveTemplateSerializer(templates, many=True).data,
        "completed":   CognitiveResultSerializer(completed, many=True).data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_cognitive_assessment(request):
    """POST /biomarkers/cognitive-assessments/submit"""
    ser = CognitiveSubmitSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    try:
        template = CognitiveAssessmentTemplate.objects.get(
            code=ser.validated_data["assessment_code"])
    except CognitiveAssessmentTemplate.DoesNotExist:
        return Response({"error": "Invalid assessment code"}, status=400)

    max_s = template.max_score
    score = ser.validated_data["total_score"]
    pct   = (score / max_s * 100) if max_s else 0
    severity = ("normal" if pct <= 20 else
                "mild"   if pct <= 40 else
                "moderate" if pct <= 60 else "severe")

    result = CognitiveAssessmentResult.objects.create(
        user=request.user, template=template,
        answers=ser.validated_data["answers"],
        total_score=score, max_score=max_s,
        percentage=round(pct, 1), severity=severity,
    )
    return Response(CognitiveResultSerializer(result).data, status=201)


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Manual entry
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_manual_entry(request):
    """POST /biomarkers/manual-entry"""
    ser = ManualEntryCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    try:
        defn = BiomarkerDefinition.objects.get(code=ser.validated_data["biomarker_code"])
    except BiomarkerDefinition.DoesNotExist:
        return Response({"error": "Unknown biomarker code"}, status=400)

    val     = ser.validated_data["value"]
    lo, hi  = defn.optimal_low or 0, defn.optimal_high or 100
    flag    = "normal" if lo * 0.3 <= val <= hi * 3 else "flagged_out_of_range"

    entry = ManualEntry.objects.create(
        user=request.user,
        biomarker=defn,
        value=val,
        notes=ser.validated_data.get("notes", ""),
        entered_by=request.user.get_full_name() or request.user.username,
        entered_by_role=getattr(getattr(request.user, "profile", None), "role", None) or "employee",
        system_validation=flag,
    )
    return Response(ManualEntrySerializer(entry).data, status=201)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def validate_manual_entry(request, entry_id):
    """PUT /biomarkers/manual-entry/<entry_id>/validate"""
    ser = ValidateEntrySerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    try:
        entry = ManualEntry.objects.select_related("biomarker").get(id=entry_id)
    except ManualEntry.DoesNotExist:
        return Response({"error": "Entry not found"}, status=404)

    approved = ser.validated_data["approved"]

    if approved:
        _ingest_bulk(entry.user, [{
            "biomarker_code": entry.biomarker.code,
            "value":          entry.value,
            "source":         "VALIDATED_MANUAL",
            "collected_at":   entry.created_at,
        }])

    entry.clinician_validation = "approved" if approved else "rejected"
    entry.clinician            = request.user
    entry.clinician_notes      = ser.validated_data.get("notes", "")
    entry.status               = "validated" if approved else "rejected"
    entry.validated_at         = dj_timezone.now()
    entry.save()

    return Response(ManualEntrySerializer(entry).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_manual_entries(request):
    """GET /biomarkers/manual-entries"""
    uid     = request.user.id
    entries = (ManualEntry.objects
               .filter(Q(user_id=uid) | Q(clinician_id=uid))
               .select_related("biomarker")
               .order_by("-created_at")[:50])
    return Response({"entries": ManualEntrySerializer(entries, many=True).data})


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Correlation matrix
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def correlation_matrix(request):
    """GET /biomarkers/correlation-matrix"""
    uid = request.user.id

    all_bms = list(BiomarkerResult.objects
                   .filter(user_id=uid)
                   .select_related("biomarker")
                   .order_by("-collected_at")[:500])

    latest = {}
    for bm in all_bms:
        if bm.biomarker.code not in latest:
            latest[bm.biomarker.code] = bm

    red_codes = {code for code, bm in latest.items() if _is_red(bm.value, bm.biomarker)}

    correlations  = []
    cascade_impact = {}

    for corr in BiomarkerCorrelation.objects.select_related("biomarker_a", "biomarker_b").all():
        a, b = corr.biomarker_a.code, corr.biomarker_b.code
        if a in red_codes or b in red_codes:
            correlations.append({
                "biomarker_a": a, "name_a": corr.biomarker_a.name,
                "biomarker_b": b, "name_b": corr.biomarker_b.name,
                "strength": corr.strength, "direction": corr.direction,
                "insight": corr.insight,
                "a_status": "red" if a in red_codes else "ok",
                "b_status": "red" if b in red_codes else "ok",
            })
            cascade_impact[a] = cascade_impact.get(a, 0) + 1
            cascade_impact[b] = cascade_impact.get(b, 0) + 1

    best_target = None
    if cascade_impact:
        best_code = max(cascade_impact, key=cascade_impact.get)
        defn      = BiomarkerDefinition.objects.get(code=best_code)
        best_target = {
            "code": best_code, "name": defn.name,
            "connections": cascade_impact[best_code],
            "recommendation": (f"Improving {defn.name} would positively impact "
                               f"{cascade_impact[best_code]} other biomarkers."),
        }

    return Response({
        "correlations":    correlations,
        "red_biomarkers":  list(red_codes),
        "cascade_impact":  cascade_impact,
        "best_target":     best_target,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 9.  Benchmarking
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def biomarker_benchmarking(request):
    """GET /biomarkers/benchmarking"""
    from django.contrib.auth.models import User as DjangoUser
    uid      = request.user.id
    profile  = getattr(request.user, "profile", None)
    user_age = getattr(profile, "age",  35)
    user_sex = getattr(profile, "sex",  "M")
    age_lo   = max(18, user_age - 10)
    age_hi   = user_age + 10

    user_bms = list(BiomarkerResult.objects
                    .filter(user_id=uid)
                    .select_related("biomarker")
                    .order_by("-collected_at")[:500])
    user_latest = {}
    for bm in user_bms:
        if bm.biomarker.code not in user_latest:
            user_latest[bm.biomarker.code] = bm.value

    # Build cohort from demo users (adapt query to your User model)
    cohort_qs = DjangoUser.objects.filter(
        profile__is_demo=True, profile__sex=user_sex,
        profile__age__gte=age_lo, profile__age__lte=age_hi,
    ).values_list("id", flat=True)
    cohort_ids   = list(cohort_qs)
    cohort_label = f"{user_sex}, Age {age_lo}-{age_hi}"

    if len(cohort_ids) < 5:
        cohort_ids   = list(DjangoUser.objects.filter(profile__is_demo=True)
                            .values_list("id", flat=True))
        cohort_label = "All Participants"

    cohort_bms = list(BiomarkerResult.objects
                      .filter(user_id__in=cohort_ids)
                      .select_related("biomarker"))
    cohort_by_code = {}
    for bm in cohort_bms:
        cohort_by_code.setdefault(bm.biomarker.code, []).append(bm.value)

    benchmarks = []
    for defn in BiomarkerDefinition.objects.all():
        user_val    = user_latest.get(defn.code)
        cohort_vals = sorted(cohort_by_code.get(defn.code, []))
        if user_val is None or len(cohort_vals) < 3:
            continue

        below      = sum(1 for v in cohort_vals if v < user_val)
        equal      = sum(1 for v in cohort_vals if v == user_val)
        percentile = round(((below + equal * 0.5) / len(cohort_vals)) * 100, 1)

        d = defn.direction
        if d == "lower_better":
            hp = round(100 - percentile, 1)
        elif d == "higher_better":
            hp = percentile
        else:
            lo, hi = defn.optimal_low or 0, defn.optimal_high or 100
            mid    = (lo + hi) / 2
            dist   = abs(user_val - mid) / max(abs(hi - lo), 1)
            hp     = round(max(0, 100 - dist * 100), 1)

        n    = len(cohort_vals)
        mean = round(sum(cohort_vals) / n, 1)
        p25  = cohort_vals[n // 4]
        p75  = cohort_vals[3 * n // 4]

        rating = ("excellent"     if hp >= 80 else
                  "good"          if hp >= 60 else
                  "average"       if hp >= 40 else
                  "below_average" if hp >= 20 else "needs_attention")

        benchmarks.append({
            "code": defn.code, "name": defn.name,
            "pillar": defn.pillar, "unit": defn.unit,
            "user_value": round(user_val, 1),
            "percentile": percentile, "health_percentile": hp,
            "cohort_mean": mean, "cohort_p25": p25, "cohort_p75": p75,
            "cohort_size": n, "direction": d, "rating": rating,
        })

    benchmarks.sort(key=lambda x: -x["health_percentile"])
    overall = round(sum(b["health_percentile"] for b in benchmarks) / max(len(benchmarks), 1), 1)
    strengths = [b for b in benchmarks if b["rating"] in ("excellent", "good")][:3]
    improve   = [b for b in sorted(benchmarks, key=lambda x: x["health_percentile"])
                 if b["rating"] in ("needs_attention", "below_average")][:3]

    return Response({
        "benchmarks": benchmarks, "cohort_label": cohort_label,
        "cohort_size": len(cohort_ids),
        "overall_health_percentile": overall,
        "top_strengths": strengths, "areas_to_improve": improve,
        "user_age": user_age, "user_sex": user_sex,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 10. Get user biomarkers
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_biomarkers(request, user_id):
    """GET /biomarkers/<user_id>"""
    results = (BiomarkerResult.objects
               .filter(user_id=user_id)
               .select_related("biomarker")
               .order_by("-ingested_at")[:500])
    return Response({
        "biomarkers": BiomarkerResultSerializer(results, many=True).data,
        "count": results.count(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# 11. Wearable devices
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_wearable_devices(request):
    """GET /wearable/devices"""
    devices     = list(WearableDevice.objects.all())
    connections = {c.device_id: c for c in
                   WearableConnection.objects.filter(user=request.user)}

    data = []
    for d in devices:
        item = WearableDeviceSerializer(d).data
        item["status"] = "available"
        conn = connections.get(d.device_id)
        if conn:
            item["status"]       = "connected"
            item["connected_at"] = conn.connected_at
            item["last_sync"]    = conn.last_sync
        data.append(item)

    return Response({"devices": data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def connect_device(request, device_id):
    """POST /wearable/connect/<device_id>"""
    try:
        device = WearableDevice.objects.get(device_id=device_id)
    except WearableDevice.DoesNotExist:
        return Response({"error": "Unsupported device"}, status=400)

    conn, created = WearableConnection.objects.get_or_create(
        user=request.user, device=device,
        defaults={"metrics_enabled": device.metrics},
    )
    if not created:
        return Response({"message": "Already connected",
                         "connection": WearableConnectionSerializer(conn).data})

    return Response({"message": "Device connected",
                     "connection": WearableConnectionSerializer(conn).data}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def disconnect_device(request, device_id):
    """POST /wearable/disconnect/<device_id>"""
    deleted, _ = WearableConnection.objects.filter(
        user=request.user, device__device_id=device_id).delete()
    if not deleted:
        return Response({"error": "Device not connected"}, status=404)
    return Response({"message": "Device disconnected", "device": device_id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_wearable(request):
    """POST /wearable/sync  {device: "oura"}"""
    ser = WearableSyncSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    device_id = ser.validated_data["device"]

    # Metric ranges per device (same as FastAPI original)
    DEVICE_METRIC_RANGES = {
        "oura":          {"hrv_rmssd": (25,60), "deep_sleep_pct": (10,25), "sleep_efficiency": (75,95), "recovery_score": (40,95)},
        "apple_health":  {"resting_hr": (50,85), "hrv_rmssd": (20,55), "sleep_duration": (5.5,9), "vo2_max": (25,50)},
        "google_health": {"resting_hr": (52,82), "sleep_duration": (5.5,8.5), "spo2": (94,99)},
        "garmin":        {"vo2_max": (25,55), "resting_hr": (48,80), "sleep_duration": (5,9), "deep_sleep_pct": (8,25)},
        "whoop":         {"hrv_rmssd": (22,65), "recovery_score": (30,98), "sleep_efficiency": (70,96)},
        "fitbit":        {"resting_hr": (55,85), "sleep_duration": (5,9), "sleep_efficiency": (70,95)},
        "withings":      {"body_fat_pct": (10,35)},
        "samsung_health":{"resting_hr": (52,84), "spo2": (94,99), "sleep_duration": (5,9)},
        "polar":         {"resting_hr": (48,78), "hrv_rmssd": (25,60), "vo2_max": (28,55)},
        "amazfit":       {"resting_hr": (50,82), "spo2": (94,99), "sleep_duration": (5.5,9)},
        "coros":         {"resting_hr": (48,78), "hrv_rmssd": (22,58), "vo2_max": (26,52)},
    }

    metrics = DEVICE_METRIC_RANGES.get(device_id, DEVICE_METRIC_RANGES["oura"])
    bm_data = [
        {"biomarker_code": code, "value": round(random.uniform(lo, hi), 1),
         "source": f"WEARABLE_{device_id.upper()}"}
        for code, (lo, hi) in metrics.items()
    ]
    saved = _ingest_bulk(request.user, bm_data)

    # update last_sync
    WearableConnection.objects.filter(
        user=request.user, device__device_id=device_id
    ).update(last_sync=dj_timezone.now())

    return Response({
        "device": device_id, "synced": True,
        "ingested": len(saved),
        "results": BiomarkerResultSerializer(saved, many=True).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_wearable_connections(request):
    """GET /wearable/connections"""
    conns = WearableConnection.objects.filter(user=request.user).select_related("device")
    return Response({"connections": WearableConnectionSerializer(conns, many=True).data})


# ─────────────────────────────────────────────────────────────────────────────
# 12. Lab upload
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_lab_results(request):
    """POST /lab/upload"""
    ser = LabUploadSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    lab_name = ser.validated_data["lab_name"]
    results  = ser.validated_data["results"]

    valid_codes = set(BiomarkerDefinition.objects.filter(
        code__in=results.keys()).values_list("code", flat=True))

    if not valid_codes:
        return Response({"error": "No valid biomarkers in lab results"}, status=400)

    bm_data = [
        {"biomarker_code": code, "value": results[code],
         "source": f"LAB_{lab_name.upper().replace(' ', '_')}"}
        for code in valid_codes
    ]
    saved = _ingest_bulk(request.user, bm_data)
    return Response({
        "lab": lab_name, "processed": True,
        "ingested": len(saved),
        "results": BiomarkerResultSerializer(saved, many=True).data,
    }, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_lab_text(request):
    """POST /lab/upload-text  {text: "..."}"""
    ser = LabTextUploadSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    text_lower = ser.validated_data["text"].lower()
    patterns = {
        "fasting_glucose": [r"(?:fasting\s+)?glucose[\s:]+(\d+\.?\d*)", r"fbs[\s:]+(\d+\.?\d*)"],
        "hba1c":           [r"hba1c[\s:]+(\d+\.?\d*)", r"glycated\s+hemo[\w]*[\s:]+(\d+\.?\d*)"],
        "ldl_c":           [r"ldl[\s\-c:]+(\d+\.?\d*)", r"ldl\s+cholesterol[\s:]+(\d+\.?\d*)"],
        "hdl_c":           [r"hdl[\s\-c:]+(\d+\.?\d*)", r"hdl\s+cholesterol[\s:]+(\d+\.?\d*)"],
        "triglycerides":   [r"triglycerides?[\s:]+(\d+\.?\d*)", r"tg[\s:]+(\d+\.?\d*)"],
        "hscrp":           [r"(?:hs[\-]?)?crp[\s:]+(\d+\.?\d*)", r"c[\-\s]?reactive[\s:]+(\d+\.?\d*)"],
        "vitamin_d":       [r"vitamin\s*d[\s:]+(\d+\.?\d*)", r"25[\-\s]?oh[\-\s]?d[\s:]+(\d+\.?\d*)"],
        "resting_hr":      [r"(?:resting\s+)?heart\s+rate[\s:]+(\d+\.?\d*)", r"pulse[\s:]+(\d+\.?\d*)"],
    }

    extracted = {}
    for code, pats in patterns.items():
        for pat in pats:
            m = re.search(pat, text_lower)
            if m:
                try:
                    extracted[code] = float(m.group(1))
                except ValueError:
                    pass
                break

    if not extracted:
        return Response({"parsed": 0,
                         "message": "No biomarkers detected. Try structured format.",
                         "extracted": {}})

    valid_codes = set(BiomarkerDefinition.objects.filter(
        code__in=extracted.keys()).values_list("code", flat=True))

    bm_data = [{"biomarker_code": c, "value": v, "source": "LAB_OCR"}
               for c, v in extracted.items() if c in valid_codes]
    saved = _ingest_bulk(request.user, bm_data)

    return Response({
        "parsed": len(extracted), "extracted": extracted,
        "ingested": len(saved),
        "results": BiomarkerResultSerializer(saved, many=True).data,
    }, status=201)


# ─────────────────────────────────────────────────────────────────────────────
# 13. Report repository
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_report_repository(request):
    """GET /reports/repository"""
    reports = (ReportRepository.objects
               .filter(user=request.user)
               .order_by("-uploaded_at")[:100])
    return Response({
        "reports": ReportRepositorySerializer(reports, many=True).data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_report(request):
    """POST /reports/upload"""
    ser = ReportUploadSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    content       = ser.validated_data.get("content", "")
    is_hps_report = ser.validated_data.get("is_hps_report", False)

    report_type       = "lab_report" if is_hps_report else "other"
    title             = "Lab Report" if is_hps_report else "General Report"
    report_date       = dj_timezone.now()
    extracted_params  = []

    # Optional: call an LLM to parse the report content if is_hps_report
    # (wire up your own LLM client here — same logic as the FastAPI version)

    report = ReportRepository.objects.create(
        user=request.user,
        report_type=report_type,
        title=title,
        is_hps_report=is_hps_report,
        uploaded_by=request.user.get_full_name() or request.user.username,
        uploaded_by_role=getattr(getattr(request.user, "profile", None), "role", "employee"),
        report_date=report_date,
        content_preview=content[:200],
        size_bytes=len(content),
        parameters_extracted=len(extracted_params),
        extracted_parameters=extracted_params,
    )
    return Response(ReportRepositorySerializer(report).data, status=201)