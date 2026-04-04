# from django.contrib import admin
# from .models import UserProfile,Question, QuestionOption, UserAnswer

# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = (
#         "id",
#         "username",
#         "email",
#         "is_google_user",
#     )

#     search_fields = (
#         "user__username",
#         "user__email",
#     )

#     list_filter = (
#         "is_google_user",
#     )

#     def username(self, obj):
#         return obj.user.username

#     def email(self, obj):
#         return obj.user.email



# class QuestionOptionInline(admin.TabularInline):
#     model = QuestionOption
#     extra = 1
    
# @admin.register(Question)
# class QuestionAdmin(admin.ModelAdmin):
#     list_display = ("id", "text", "question_type", "order", "is_required")
#     list_filter = ("question_type",)
#     ordering = ("order", "id")
#     inlines = [QuestionOptionInline]


# @admin.register(UserAnswer)
# class UserAnswerAdmin(admin.ModelAdmin):
#     list_display = (
#         "user",
#         "question",
#         "selected_option",
#         "answer_number",
#         "answer_date",
#         "created_at",
#     )
#     list_filter = ("question__question_type",)
#     readonly_fields = ("created_at",)


from django.contrib import admin
from .models import (
    Role,
    Company,
    Location,
    Department,
    Plan,
    UserProfile,
    EmployeePlan,
    Question,
    QuestionOption,
    UserAnswer,
    Challenge,ChallengeParticipant,
    CreditTransaction,
    BiomarkerDefinition, PillarConfig, BiomarkerResult,
    ManualEntry, BiomarkerCorrelation,
    WearableDevice, WearableConnection,
    CognitiveAssessmentTemplate, CognitiveAssessmentResult,
    ReportRepository,
    HPSScore, SupportTicket, CCAssignment, CCAlert, CCSession, CCProtocol,
    Appointment, MemberMedicalHistory, VitalsLog, EMREncounter,
    NutritionLog, NutritionPlan,
    PlatformAnnouncement, AuditLog, EmployeeLeave, PayrollRecord,
    HelpdeskTicket, PharmacyInventory, CompanyContract,
    PlatformStat, StrategicObjective,
    # Adding missing ones:
    CCPrescription, CCMessage, CCOverrideAudit, CCReferral,
    PharmacyCatalogItem, PharmacyOrder, PharmacyOrderItem,
    Asset, LeaveBalance, EHSScore, BRIScore, CorpBiomarkerResult,
    CorpWearableConnection, LabPartner, LabPanel, LabOrder,
    NudgeCampaign, HREscalation, CareTeamEscalation, WellnessProgramme,
    Intervention, FranchiseSeason, SocialPost, SocialComment,
    UserBadge, CreditBalance, Notification, WhatsappLog,
    VideoConsultation, TelehealthSession, Phlebotomist, SampleBooking,
    PhlebotomistJob, Roadmap, RoadmapReview, LongevityProtocol,
    Referral, CarePlanGoal, CareTeam, CareAppointment,
    CareReview, MentalAssessment, CAAssessment, AdaptiveAssessment,
    OutcomeCycle, HealthBrief, PrivacySetting, Season,
    Medication, LabReport, AITrainingRecord, ChatMessage,
    UserAddress, HCPProfile, HealthSnapshot, DailyChallenge,
    BadgeCatalog, DopamineChallengeTemplate, OrganSystem,
    AppointmentService, MedicalCondition, MedicationLog,
    RefillRequest, SOSAlert, CarePlan,EMRAllergy, DiagnosticOrder,
    DiagnosticCatalog,CareTeamMember
)

from django.db import models


def get_all_fields(model):
    return [field.name for field in model._meta.fields]


def get_searchable_fields(model):
    searchable_types = (
        models.CharField,
        models.TextField,
        models.EmailField,
        models.SlugField,
    )

    return [
        field.name
        for field in model._meta.fields
        if isinstance(field, searchable_types)
    ]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Role)
    search_fields = get_searchable_fields(Role)





@admin.register(CareTeamMember)
class CareTeamMemberAdmin(admin.ModelAdmin):
    list_display = get_all_fields(CareTeamMember)
    search_fields = get_searchable_fields(CareTeamMember)



@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Company)
    search_fields = get_searchable_fields(Company)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Location)
    search_fields = get_searchable_fields(Location)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Department)
    search_fields = get_searchable_fields(Department)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Plan)
    search_fields = get_searchable_fields(Plan)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = get_all_fields(UserProfile)
    search_fields = get_searchable_fields(UserProfile) + [
        "user__username",
        "user__email",
    ]


@admin.register(EmployeePlan)
class EmployeePlanAdmin(admin.ModelAdmin):
    list_display = get_all_fields(EmployeePlan)
    search_fields = ("user__username", "plan__name")

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Challenge)
    search_fields = get_searchable_fields(Challenge)

@admin.register(ChallengeParticipant)
class ChallengeParticipantAdmin(admin.ModelAdmin):
    list_display = get_all_fields(ChallengeParticipant)
    search_fields = get_searchable_fields(ChallengeParticipant)

@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = get_all_fields(CreditTransaction)
    search_fields = get_searchable_fields(CreditTransaction)




"""biomarkers/admin.py"""



@admin.register(BiomarkerDefinition)
class BiomarkerDefinitionAdmin(admin.ModelAdmin):
    list_display  = ["code", "name", "pillar", "unit", "direction", "data_source"]
    list_filter   = ["pillar", "direction", "data_source"]
    search_fields = ["code", "name"]


@admin.register(PillarConfig)
class PillarConfigAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "color"]


@admin.register(BiomarkerResult)
class BiomarkerResultAdmin(admin.ModelAdmin):
    list_display  = ["user", "biomarker", "value", "source", "collected_at"]
    list_filter   = ["source", "biomarker__pillar"]
    search_fields = ["user__username", "biomarker__code"]
    date_hierarchy = "collected_at"


@admin.register(ManualEntry)
class ManualEntryAdmin(admin.ModelAdmin):
    list_display  = ["user", "biomarker", "value", "status", "system_validation",
                     "clinician_validation", "created_at"]
    list_filter   = ["status", "system_validation", "clinician_validation"]
    search_fields = ["user__username", "biomarker__code"]


@admin.register(BiomarkerCorrelation)
class BiomarkerCorrelationAdmin(admin.ModelAdmin):
    list_display  = ["biomarker_a", "biomarker_b", "strength", "direction"]
    list_filter   = ["direction"]


@admin.register(WearableDevice)
class WearableDeviceAdmin(admin.ModelAdmin):
    list_display  = ["device_id", "name", "category"]
    list_filter   = ["category"]


@admin.register(WearableConnection)
class WearableConnectionAdmin(admin.ModelAdmin):
    list_display  = ["user", "device", "status", "connected_at", "last_sync"]
    list_filter   = ["status", "device"]


@admin.register(CognitiveAssessmentTemplate)
class CognitiveAssessmentTemplateAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "domain", "pillar", "max_score"]


@admin.register(CognitiveAssessmentResult)
class CognitiveAssessmentResultAdmin(admin.ModelAdmin):
    list_display  = ["user", "template", "total_score", "severity", "completed_at"]
    list_filter   = ["severity", "template"]


@admin.register(ReportRepository)
class ReportRepositoryAdmin(admin.ModelAdmin):
    list_display  = ["user", "title", "report_type", "is_hps_report",
                     "parameters_extracted", "uploaded_at"]
    list_filter   = ["report_type", "is_hps_report", "privacy_level"]


@admin.register(HPSScore)
class HPSScoreAdmin(admin.ModelAdmin):
    list_display = ["user", "hps_final", "tier", "timestamp"]
    list_filter = ["tier"]

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ["user", "subject", "status", "priority", "created_at"]
    list_filter = ["status", "priority", "category"]

@admin.register(CCAssignment)
class CCAssignmentAdmin(admin.ModelAdmin):
    list_display = ["member", "cc", "role", "created_at"]
    list_filter = ["role"]

@admin.register(CCAlert)
class CCAlertAdmin(admin.ModelAdmin):
    list_display = ["member", "severity", "status", "created_at"]
    list_filter = ["severity", "status"]

@admin.register(CCSession)
class CCSessionAdmin(admin.ModelAdmin):
    list_display = ["cc", "member", "session_type", "scheduled_at", "duration_min"]

@admin.register(CCProtocol)
class CCProtocolAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at", "duration_weeks"]

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["member", "assigned_hcp", "appointment_type", "mode", "scheduled_at", "status"]
    list_filter = ["appointment_type", "status", "mode"]

@admin.register(MemberMedicalHistory)
class MemberMedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ["member", "updated_at"]

@admin.register(VitalsLog)
class VitalsLogAdmin(admin.ModelAdmin):
    list_display = ["member", "recorded_at", "recorded_by"]

@admin.register(EMREncounter)
class EMREncounterAdmin(admin.ModelAdmin):
    list_display = ["member", "hcp", "encounter_type", "created_at"]

@admin.register(NutritionLog)
class NutritionLogAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "meal_type", "total_calories", "logged_at"]

@admin.register(NutritionPlan)
class NutritionPlanAdmin(admin.ModelAdmin):
    list_display = ["user", "goal", "generated_at"]

@admin.register(PlatformAnnouncement)
class PlatformAnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "target_role", "is_active", "created_at"]
    list_filter = ["is_active", "target_role"]

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "resource", "timestamp"]
    list_filter = ["action"]

@admin.register(EmployeeLeave)
class EmployeeLeaveAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "start_date", "end_date", "status"]
    list_filter = ["status", "leave_type"]

@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ["employee", "period_start", "period_end", "net_pay", "status"]
    list_filter = ["status"]

@admin.register(HelpdeskTicket)
class HelpdeskTicketAdmin(admin.ModelAdmin):
    list_display = ["employee", "subject", "category", "priority", "status"]
    list_filter = ["status", "category", "priority"]

@admin.register(PharmacyInventory)
class PharmacyInventoryAdmin(admin.ModelAdmin):
    list_display = ["item_code", "name", "category", "quantity", "reorder_level"]
    list_filter = ["category"]

@admin.register(CompanyContract)
class CompanyContractAdmin(admin.ModelAdmin):
    list_display = ["company", "plan_tier", "is_active", "start_date", "end_date"]
    list_filter = ["plan_tier", "is_active"]

@admin.register(PlatformStat)
class PlatformStatAdmin(admin.ModelAdmin):
    list_display = ["date", "metric_name", "metric_value", "company"]
    list_filter = ["metric_name"]

@admin.register(StrategicObjective)
class StrategicObjectiveAdmin(admin.ModelAdmin):
    list_display = ["title", "department", "status", "deadline", "owner"]
    list_filter = ["status", "department"]
#  Automated Registration for remaining models 

MISSING_MODELS = [
    CCPrescription, CCMessage, CCOverrideAudit, CCReferral,
    PharmacyCatalogItem, PharmacyOrder, PharmacyOrderItem,
    Asset, LeaveBalance, EHSScore, BRIScore, CorpBiomarkerResult,
    CorpWearableConnection, LabPartner, LabPanel, LabOrder,
    NudgeCampaign, HREscalation, CareTeamEscalation, WellnessProgramme,
    Intervention, FranchiseSeason, SocialPost, SocialComment,
    UserBadge, CreditBalance, Notification, WhatsappLog,
    VideoConsultation, TelehealthSession, Phlebotomist, SampleBooking,
    PhlebotomistJob, Roadmap, RoadmapReview, LongevityProtocol,
    Referral, CarePlanGoal, CareTeam, CareAppointment,
    CareReview, MentalAssessment, CAAssessment, AdaptiveAssessment,
    OutcomeCycle, HealthBrief, PrivacySetting, Season,
    Medication, LabReport, AITrainingRecord, ChatMessage,
    UserAddress, HCPProfile, HealthSnapshot, DailyChallenge,
    BadgeCatalog, DopamineChallengeTemplate, OrganSystem,
    AppointmentService, MedicalCondition, MedicationLog,
    RefillRequest, SOSAlert, CarePlan,
    EMRAllergy, DiagnosticOrder, DiagnosticCatalog
]

for model in MISSING_MODELS:
    try:
        @admin.register(model)
        class DynamicAdmin(admin.ModelAdmin):
            list_display = [f.name for f in model._meta.fields if not f.is_relation][:8]
            search_fields = [f.name for f in model._meta.fields if isinstance(f, (models.CharField, models.TextField))][:5]
    except Exception:
        pass # Already registered or error
