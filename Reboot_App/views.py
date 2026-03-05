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
    QuestionOptionSerializer,)
from allauth.socialaccount.models import SocialAccount
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated,IsAdminUser
from .utils import generate_otp, send_otp_email, otp_expiry_time
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .models import (UserProfile,Question,UserAnswer,Role,Location,
 Department, Plan, EmployeePlan,Challenge,ChallengeParticipant,Company,QuestionOption)
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
            "role_name": profile.role.name if profile.role else None,
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