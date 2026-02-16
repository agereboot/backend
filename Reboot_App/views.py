from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, LoginSerializer,QuestionSerializer,UserAnswerSerializer,ExcelUploadSerializer
from allauth.socialaccount.models import SocialAccount
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from .utils import generate_otp, send_otp_email, otp_expiry_time
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .models import UserProfile,Question,UserAnswer,Role, Location, Department, Plan, EmployeePlan
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
from django.db.models import Count, Q



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

    return Response({
        "success": True,
        "message": "Login successful",
        "data": {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
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


# ==========================================
# BULK EMPLOYEE UPLOAD
# ==========================================
# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def bulk_employee_upload(request):

#     REQUIRED_HEADERS = [
#         "first_name",
#         "last_name",
#         "email",
#         "phone_number",
#         "location",
#         "department",
#         "plan",
#     ]

#     serializer = ExcelUploadSerializer(data=request.data)
#     if not serializer.is_valid():
#         return Response(serializer.errors, status=400)

#     file = serializer.validated_data["file"]

#     # read excel
#     try:
#         df = pd.read_excel(file)
#     except Exception:
#         return Response({"error": "Invalid Excel file"}, status=400)

#     # validate headers
#     if list(df.columns) != REQUIRED_HEADERS:
#         return Response(
#             {"error": "Invalid file format", "expected": REQUIRED_HEADERS},
#             status=400,
#         )

#     hr_profile = request.user.profile
#     company = hr_profile.company

#     if not company:
#         return Response({"error": "HR has no company assigned"}, status=400)

#     employee_role = Role.objects.get(name="employee")

#     df = df.dropna(how="all")

#     created_users = []
#     errors = []

#     for index, row in df.iterrows():
#         try:
#             first_name = str(row["first_name"]).strip()
#             last_name = str(row["last_name"]).strip()
#             email = str(row["email"]).strip()
#             phone = str(row["phone_number"]).strip()
#             location_name = str(row["location"]).strip()
#             department_name = str(row["department"]).strip()
#             plan_name = str(row["plan"]).strip().lower()

#             if not email:
#                 continue

#             username = generate_username(first_name, last_name)
#             temp_password = generate_temp_password()


#             # create user
#             user = User.objects.create(
#                 username=username,
#                 email=email,
#                 first_name=first_name,
#                 last_name=last_name,
#             )
#             user.set_password(temp_password)
#             user.save()

#             # location & department
#             location, department = get_location_department(
#                 company, location_name, department_name
#             )

#             # update profile
#             profile = user.profile
#             profile.phone_number = phone
#             profile.company = company
#             profile.role = employee_role
#             profile.location = location
#             profile.department = department
#             profile.invite_status = "registered"
#             profile.is_email_verified = True
#             profile.save()

#             # assign plan
#             if plan_name:
#                 plan = Plan.objects.get(name=plan_name)
#                 assign_plan_to_user(user, plan)

#             # ✅ GENERATE SECURE RESET TOKEN (your function)
#             token = generate_reset_token(user)

#             # ✅ CREATE RESET LINK WITH TOKEN
#             reset_link = f"http://localhost:3000/reset-password/{token}"

#             # ✅ SEND EMAIL
#             send_reset_password_email(user, temp_password, reset_link)

#             # update invite status
#             profile.invite_status = "invited"
#             profile.save()

#             created_users.append(username)

#         except Exception as e:
#             errors.append(f"Row {index+2}: {str(e)}")

#     return Response(
#         {
#             "created_users": created_users,
#             "errors": errors,
#             "total_created": len(created_users),
#         }
#     )


import pandas as pd
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


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
                    reset_link = f"http://localhost:3000/reset-password/{token}"
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
        user = UserProfile.objects.get(email=email)
    except UserProfile.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    token = generate_reset_token(user)

    send_reset_password_email(user, token)

    user.status = "invited"
    user.save()

    return Response({"message": "Invitation sent"})




@api_view(["POST"])
def reset_password(request):

    token = request.data.get("token")
    new_password = request.data.get("password")

    if not token or not new_password:
        return Response(
            {"error": "Token and password required"},
            status=400
        )

    try:
        user = UserProfile.objects.get(reset_token=token)
    except UserProfile.DoesNotExist:
        return Response({"error": "Invalid token"}, status=400)

    if not is_token_valid(user, token):
        return Response({"error": "Token expired"}, status=400)

    user.password = make_password(new_password)
    user.status = "active"

    clear_reset_token(user)

    user.save()

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


 
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employees_list_api(request):

    company = request.user.profile.company
    if not company:
        return Response({"error": "No company assigned"}, status=400)

    # ------------------------------------------------
    # ❌ BLOCK WRONG QUERY KEYS (STRICT API)
    # ------------------------------------------------
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

    # ------------------------------------------------
    # FILTER PARAMS
    # ------------------------------------------------
    department_id = request.GET.get("department_id")
    location_id = request.GET.get("location_id")
    status_filter = request.GET.get("status")

    # ------------------------------------------------
    # ❌ TYPE VALIDATION (NO ORM CRASH)
    # ------------------------------------------------
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

    # ------------------------------------------------
    # BASE QUERY (FAST)
    # ------------------------------------------------
    profiles_qs = (
        UserProfile.objects
        .select_related("user", "department", "location", "role")
        .filter(company=company, role__name="employee")
    )

    # ------------------------------------------------
    # APPLY FILTERS
    # ------------------------------------------------
    if department_id:
        profiles_qs = profiles_qs.filter(department_id=int(department_id))

    if location_id:
        profiles_qs = profiles_qs.filter(location_id=int(location_id))

    if status_filter:
        profiles_qs = profiles_qs.filter(invite_status=status_filter)

    # ------------------------------------------------
    # PREFETCH ACTIVE PLANS
    # ------------------------------------------------
    profiles_qs = profiles_qs.prefetch_related("user__employeeplan_set")
    print('profiles_qs',profiles_qs)

    # ------------------------------------------------
    # EMPLOYEE LIST 
    # ------------------------------------------------
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

    # ==================================================
    # 📊 SUMMARY COUNTS (NO FILTERS)
    # ==================================================
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

    # ------------------------------------------------
    # FINAL RESPONSE
    # ------------------------------------------------
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

    # -----------------------------
    # UPDATE USER FIELDS
    # -----------------------------
    user.first_name = data.get("first_name", user.first_name)
    user.last_name = data.get("last_name", user.last_name)
    user.save(update_fields=["first_name", "last_name"])

    # -----------------------------
    # UPDATE PROFILE FIELDS
    # -----------------------------
    if "phone_number" in data:
        profile.phone_number = data["phone_number"]

    if "invite_status" in data:
        profile.invite_status = data["invite_status"]

    # -----------------------------
    # DEPARTMENT UPDATE
    # -----------------------------
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

    # -----------------------------
    # LOCATION UPDATE
    # -----------------------------
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

    # -----------------------------
    # PLAN UPDATE (REPLACE ACTIVE)
    # -----------------------------
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

    # -----------------------------
    # RESPONSE
    # -----------------------------
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
