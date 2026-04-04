from rest_framework import serializers
from .models import (
    EHSScore, BRIScore, Intervention, HREscalation, 
    CareTeamEscalation, NudgeCampaign, WellnessProgramme, 
    FranchiseSeason, CompanyContract, PlatformStat, StrategicObjective
)
from django.contrib.auth.models import User

class EHSScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = EHSScore
        fields = '__all__'

class BRIScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = BRIScore
        fields = '__all__'

class InterventionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)

    class Meta:
        model = Intervention
        fields = '__all__'

class HREscalationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = HREscalation
        fields = '__all__'

class CareTeamEscalationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    escalated_by_name = serializers.CharField(source='escalated_by.get_full_name', read_only=True)

    class Meta:
        model = CareTeamEscalation
        fields = '__all__'

class NudgeCampaignSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = NudgeCampaign
        fields = '__all__'

class WellnessProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellnessProgramme
        fields = '__all__'

class FranchiseSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = FranchiseSeason
        fields = '__all__'

class CompanyContractSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = CompanyContract
        fields = '__all__'

class PlatformStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformStat
        fields = '__all__'

class StrategicObjectiveSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)

    class Meta:
        model = StrategicObjective
        fields = '__all__'
