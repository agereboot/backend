from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, LoginSerializer,QuestionSerializer,UserAnswerSerializer
from allauth.socialaccount.models import SocialAccount
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from .utils import generate_otp, send_otp_email, otp_expiry_time
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .models import UserProfile,Question,UserAnswer

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
