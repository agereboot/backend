from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile,Question, QuestionOption, UserAnswer


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def validate_phone_number(self, value):
        if UserProfile.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match"
            })
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        phone_number = validated_data.pop("phone_number")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", "")
        )

        # ✅ UPDATE existing profile (created by signal)
        profile = user.profile
        profile.phone_number = phone_number
        profile.is_google_user = False
        profile.save()

        return user

class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username_or_email = data.get("username_or_email")
        password = data.get("password")

        user = (
            User.objects.filter(email=username_or_email).first() or
            User.objects.filter(username=username_or_email).first()
        )

        if not user:
            raise serializers.ValidationError("User not found")

        user = authenticate(username=user.username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        if not user.profile.is_email_verified:
            raise serializers.ValidationError("Email not verified")

        data["user"] = user
        return data


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ("id", "label")


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "text",
            "question_type",
            "order",
            "is_required",
            "options",
        )


class UserAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAnswer
        fields = (
            "question",
            "selected_option",
            "answer_number",
            "answer_date",
        )

    def validate(self, data):
        question = data["question"]

        if question.question_type == "single_choice" and not data.get("selected_option"):
            raise serializers.ValidationError("Option is required")

        if question.question_type in ["number", "slider"] and data.get("answer_number") is None:
            raise serializers.ValidationError("Number is required")

        if question.question_type == "date" and not data.get("answer_date"):
            raise serializers.ValidationError("Date is required")

        return data
