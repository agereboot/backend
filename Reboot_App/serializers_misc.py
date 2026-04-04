from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    MentalAssessment, CareTeamMember, CareTeamReview, 
    CreditTransaction, Season, PrivacySetting, UserProfile
)

class MentalAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentalAssessment
        fields = "__all__"

class CareTeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareTeamMember
        fields = "__all__"

class CareTeamReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    class Meta:
        model = CareTeamReview
        fields = "__all__"

class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = "__all__"

class SeasonSerializer(serializers.ModelSerializer):
    participant_count = serializers.IntegerField(source="participants.count", read_only=True)
    class Meta:
        model = Season
        fields = "__all__"

class PrivacySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacySetting
        fields = "__all__"

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["age", "gender", "height_cm", "weight_kg", "ethnicity", "franchise", "sex"]
