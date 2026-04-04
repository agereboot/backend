from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    CoachTask, FitnessProfile, ExerciseProgramme, ExerciseSessionLog,
    CBTModule, CBTAssignment, TherapyNote, CrisisAlert, BehaviorLog,
    NutritionalProfile, MealPlan, SupplementStack, Habit, HabitLog,
    CheckIn, BodyComposition, Goal, ResourceShare,
    TherapyProgram, MealPlanDay, NutritionConsultationNote, HCPProfile, Escalation
)

class CoachTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachTask
        fields = "__all__"

class FitnessProfileSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source="member.get_full_name")
    class Meta:
        model = FitnessProfile
        fields = "__all__"

class ExerciseProgrammeSerializer(serializers.ModelSerializer):
    coach_name = serializers.ReadOnlyField(source="coach.get_full_name")
    member_name = serializers.ReadOnlyField(source="member.get_full_name")
    class Meta:
        model = ExerciseProgramme
        fields = "__all__"

class ExerciseSessionLogSerializer(serializers.ModelSerializer):
    coach_name = serializers.ReadOnlyField(source="coach.get_full_name")
    member_name = serializers.ReadOnlyField(source="member.get_full_name")
    class Meta:
        model = ExerciseSessionLog
        fields = "__all__"

class CBTModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CBTModule
        fields = "__all__"

class CBTAssignmentSerializer(serializers.ModelSerializer):
    module_name = serializers.ReadOnlyField(source="module.name")
    class Meta:
        model = CBTAssignment
        fields = "__all__"

class TherapyProgramSerializer(serializers.ModelSerializer):
    therapist_name = serializers.ReadOnlyField(source="therapist.get_full_name")
    member_name = serializers.ReadOnlyField(source="member.get_full_name")
    class Meta:
        model = TherapyProgram
        fields = "__all__"

class TherapyNoteSerializer(serializers.ModelSerializer):
    therapist_name = serializers.ReadOnlyField(source="therapist.get_full_name")
    class Meta:
        model = TherapyNote
        fields = "__all__"

class CrisisAlertSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source="member.get_full_name")
    class Meta:
        model = CrisisAlert
        fields = "__all__"

class BehaviorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorLog
        fields = "__all__"

class NutritionalProfileSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source="member.get_full_name")
    class Meta:
        model = NutritionalProfile
        fields = "__all__"

class MealPlanSerializer(serializers.ModelSerializer):
    coach_name = serializers.ReadOnlyField(source="coach.get_full_name")
    member_name = serializers.ReadOnlyField(source="member.get_full_name")
    class Meta:
        model = MealPlan
        fields = "__all__"

class MealPlanDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlanDay
        fields = "__all__"

class NutritionConsultationNoteSerializer(serializers.ModelSerializer):
    nutritionist_name = serializers.ReadOnlyField(source="nutritionist.get_full_name")
    member_name = serializers.ReadOnlyField(source="member.get_full_name")
    class Meta:
        model = NutritionConsultationNote
        fields = "__all__"

class SupplementStackSerializer(serializers.ModelSerializer):
    coach_name = serializers.ReadOnlyField(source="coach.get_full_name")
    class Meta:
        model = SupplementStack
        fields = "__all__"

class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = "__all__"

class HabitLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitLog
        fields = "__all__"

class CheckInSerializer(serializers.ModelSerializer):
    conducted_by_name = serializers.ReadOnlyField(source="conducted_by.get_full_name")
    class Meta:
        model = CheckIn
        fields = "__all__"

class BodyCompositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyComposition
        fields = "__all__"

class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = "__all__"

class ResourceShareSerializer(serializers.ModelSerializer):
    shared_by_name = serializers.ReadOnlyField(source="shared_by.get_full_name")
    class Meta:
        model = ResourceShare
        fields = "__all__"

class HCPProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source="user.get_full_name")
    class Meta:
        model = HCPProfile
        fields = "__all__"

class EscalationSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source="member.get_full_name")
    created_by_name = serializers.ReadOnlyField(source="created_by.get_full_name")
    class Meta:
        model = Escalation
        fields = "__all__"
