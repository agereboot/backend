from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers_auth import LegacyRegisterSerializer, LegacyUserSerializer
from .models import UserProfile
import random
from datetime import timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = LegacyRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        safe_user = LegacyUserSerializer(user).data
        return Response({
            "token": str(refresh.access_token),
            "user": safe_user
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get("email")
    password = request.data.get("password")
    
    user = User.objects.filter(email=email).first()
    if not user or not user.check_password(password):
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        
    refresh = RefreshToken.for_user(user)
    safe_user = LegacyUserSerializer(user).data
    return Response({
        "token": str(refresh.access_token),
        "user": safe_user
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_me(request):
    safe_user = LegacyUserSerializer(request.user).data
    return Response(safe_user)

@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    email = request.data.get("email")
    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"detail": "No account with this email"}, status=404)
        
    otp_code = str(random.randint(100000, 999999))
    profile = user.profile
    profile.email_otp = otp_code
    profile.otp_expires_at = timezone.now() + timedelta(minutes=10)
    profile.save()
    
    logger.info(f"OTP for {email}: {otp_code} (simulated)")
    return Response({
        "message": "OTP sent successfully", 
        "email": email, 
        "otp_preview": otp_code
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get("email")
    otp = request.data.get("otp")
    
    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"detail": "User not found"}, status=404)
        
    profile = user.profile
    if not profile.email_otp or profile.email_otp != otp:
        return Response({"detail": "Invalid OTP"}, status=400)
        
    if timezone.now() > profile.otp_expires_at:
        return Response({"detail": "OTP expired"}, status=400)
        
    # Clear OTP
    profile.email_otp = ""
    profile.otp_expires_at = None
    profile.is_email_verified = True
    profile.save()
    
    refresh = RefreshToken.for_user(user)
    safe_user = LegacyUserSerializer(user).data
    return Response({
        "token": str(refresh.access_token),
        "user": safe_user
    })
