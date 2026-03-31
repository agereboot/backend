from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import (
    Role, Company, Location, Department, Plan,
    UserProfile, Question, QuestionOption,UserAnswer,BiomarkerDefinition, BiomarkerResult, ManualEntry,
    BiomarkerCorrelation, WearableDevice, WearableConnection,
    CognitiveAssessmentTemplate, CognitiveAssessmentResult,
    ReportRepository, PillarConfig,
    HPSScore, SupportTicket, CCAssignment, CCAlert, CCSession, CCProtocol,
    Appointment, MemberMedicalHistory, VitalsLog, EMREncounter,
    NutritionLog, NutritionPlan
)

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



#QuestionOptionInlineSerializer
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



class ExcelUploadSerializer(serializers.Serializer):
    file = serializers.FileField()



class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]
class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "status", "created_at"]
        read_only_fields = ["created_at"]

class LocationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Location
        fields = ["id", "company", "company_name", "name"]


class DepartmentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Department
        fields = ["id", "company", "company_name", "name"]


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "price", "duration_days", "features"]



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "user", "phone_number", "is_google_user",
            "company", "company_name",
            "role", "role_name",
            "location", "location_name",
            "department", "department_name",
            "invite_status", "password_reset_required",
            "is_email_verified", "is_phone_verified",
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Used for partial updates by admin (excludes sensitive OTP/token fields)."""
    class Meta:
        model = UserProfile
        fields = [
            "phone_number", "company", "role", "location",
            "department", "invite_status", "password_reset_required",
            "is_email_verified", "is_phone_verified",
        ]

class QuestionOptionSerializer2(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "question", "label"]


class QuestionWriteSerializer(serializers.ModelSerializer):
    """Write serializer — options are managed via their own endpoint."""
    class Meta:
        model = Question
        fields = ["id", "text", "question_type", "order", "is_required"]


class BiomarkerDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BiomarkerDefinition
        fields = ["code", "name", "domain", "pillar", "unit", "direction",
                  "optimal_low", "optimal_high", "data_source"]


class BiomarkerResultSerializer(serializers.ModelSerializer):
    biomarker_code = serializers.CharField(source="biomarker.code", read_only=True)
    name           = serializers.CharField(source="biomarker.name", read_only=True)
    unit           = serializers.CharField(source="biomarker.unit", read_only=True)
    domain         = serializers.CharField(source="biomarker.domain", read_only=True)
    pillar         = serializers.CharField(source="biomarker.pillar", read_only=True)

    class Meta:
        model  = BiomarkerResult
        fields = ["id", "biomarker_code", "name", "value", "unit",
                  "domain", "pillar", "source", "collected_at", "ingested_at"]


# ── Ingest ──────────────────────────────────────────────────────────────────

class SingleBiomarkerIngestSerializer(serializers.Serializer):
    biomarker_code = serializers.CharField()
    value          = serializers.FloatField()
    source         = serializers.CharField(default="MANUAL")
    collected_at   = serializers.DateTimeField(required=False, allow_null=True)


class BulkBiomarkerIngestSerializer(serializers.Serializer):
    biomarkers = SingleBiomarkerIngestSerializer(many=True)


# ── Manual Entry ─────────────────────────────────────────────────────────────

class ManualEntrySerializer(serializers.ModelSerializer):
    biomarker_code = serializers.CharField(source="biomarker.code", read_only=True)
    biomarker_name = serializers.CharField(source="biomarker.name", read_only=True)
    unit           = serializers.CharField(source="biomarker.unit", read_only=True)

    class Meta:
        model  = ManualEntry
        fields = ["id", "biomarker_code", "biomarker_name", "value", "unit",
                  "notes", "entered_by", "entered_by_role",
                  "system_validation", "clinician_validation",
                  "status", "created_at", "validated_at",
                  "clinician_notes"]


class ManualEntryCreateSerializer(serializers.Serializer):
    biomarker_code = serializers.CharField()
    value          = serializers.FloatField()
    notes          = serializers.CharField(required=False, allow_blank=True)


class ValidateEntrySerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    notes    = serializers.CharField(required=False, allow_blank=True)


# ── Cognitive ─────────────────────────────────────────────────────────────────

class CognitiveTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CognitiveAssessmentTemplate
        fields = "__all__"


class CognitiveResultSerializer(serializers.ModelSerializer):
    assessment_code = serializers.CharField(source="template.code", read_only=True)
    assessment_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model  = CognitiveAssessmentResult
        fields = ["id", "assessment_code", "assessment_name", "answers",
                  "total_score", "max_score", "percentage", "severity", "completed_at"]


class CognitiveSubmitSerializer(serializers.Serializer):
    assessment_code = serializers.CharField()
    answers         = serializers.ListField(child=serializers.IntegerField())
    total_score     = serializers.IntegerField()


# ── Wearable ─────────────────────────────────────────────────────────────────

class WearableDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = WearableDevice
        fields = ["device_id", "name", "category", "icon", "metrics"]


class WearableConnectionSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    category    = serializers.CharField(source="device.category", read_only=True)

    class Meta:
        model  = WearableConnection
        fields = ["id", "device_id", "device_name", "category",
                  "connected_at", "last_sync", "status", "mode", "metrics_enabled"]


class WearableSyncSerializer(serializers.Serializer):
    device = serializers.CharField()


# ── Lab ───────────────────────────────────────────────────────────────────────

class LabUploadSerializer(serializers.Serializer):
    lab_name = serializers.CharField()
    results  = serializers.DictField(child=serializers.FloatField())   # {code: value}


class LabTextUploadSerializer(serializers.Serializer):
    text = serializers.CharField()


# ── Reports ───────────────────────────────────────────────────────────────────

class ReportRepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = ReportRepository
        fields = ["id", "report_type", "title", "is_hps_report",
                  "uploaded_by", "uploaded_by_role", "uploaded_at",
                  "report_date", "content_preview", "size_bytes",
                  "privacy_level", "parameters_extracted", "extracted_parameters"]


class ReportUploadSerializer(serializers.Serializer):
    content       = serializers.CharField(required=False, allow_blank=True)
    is_hps_report = serializers.BooleanField(default=False)


# ── Compare ───────────────────────────────────────────────────────────────────

class CompareSerializer(serializers.Serializer):
    code_b = serializers.CharField()

# ──────────────────────────────────────────────
# HPS & Analytics
# ──────────────────────────────────────────────

class HPSScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = HPSScore
        fields = "__all__"
        read_only_fields = ["id", "timestamp", "audit_hash"]

# ──────────────────────────────────────────────
# Support & Ticketing
# ──────────────────────────────────────────────

class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "resolved_at"]

# ──────────────────────────────────────────────
# Care Coordination (CC)
# ──────────────────────────────────────────────

class CCAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CCAssignment
        fields = "__all__"
        read_only_fields = ["id", "assigned_at"]

class CCAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = CCAlert
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

class CCSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CCSession
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

class CCProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = CCProtocol
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

# ──────────────────────────────────────────────
# EMR & Appointments
# ──────────────────────────────────────────────

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

class MemberMedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberMedicalHistory
        fields = "__all__"
        read_only_fields = ["updated_at"]

class VitalsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalsLog
        fields = "__all__"
        read_only_fields = ["id", "recorded_at"]

class EMREncounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EMREncounter
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

# ──────────────────────────────────────────────
# Nutrition
# ──────────────────────────────────────────────

class NutritionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionLog
        fields = "__all__"
        read_only_fields = ["id", "logged_at"]

class NutritionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionPlan
        fields = "__all__"
        read_only_fields = ["generated_at"]
