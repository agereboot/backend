
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid




class Role(models.Model):
    ROLE_CHOICES = (
        ("super_admin", "Super Admin"),
        ("hr_admin", "HR Admin"),   
        ("employee", "Employee"),
         ("longevity_physician",     "Longevity Physician"),
        ("fitness_coach",           "Fitness Coach"),
        ("psychologist",            "Psychologist"),
        ("physical_therapist",      "Physical Therapist"),
        ("nutritional_coach",       "Nutritional Coach"),
        ("nurse_navigator",         "Nurse Navigator"),
        ("corporate_hr_admin",      "Corporate HR Admin"),
        ("corporate_wellness_head", "Corporate Wellness Head"),
        ("cxo_executive",           "CXO Executive"),
        ("support_agent",           "Support Agent"),
        ("clinician",               "Clinician"),
        ("coach",                   "Coach"),
        ("medical_director",        "Medical Director"),
        ("clinical_admin",          "Clinical Admin"),
        ("phlebotomist",            "Phlebotomist"),
    )

    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)

    def __str__(self):
        return self.name


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    industry = models.CharField(max_length=100, default="Technology")
    admin_email = models.EmailField(blank=True, null=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Location(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="locations"
    )
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("company", "name")

    def __str__(self):
        return f"{self.company.name} - {self.name}"

class Department(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.company.name} - {self.name}"

class Plan(models.Model):
    PLAN_CHOICES = (
        ("rookie_league", "Rookie League"),
        ("velocity_circuit", "Velocity Circuit"),
        ("titan_arena", "Titan Arena"),
        ("apex_nexus", "Apex Nexus"),
    )

    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.IntegerField()
    features = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    INVITE_STATUS = (
        ("invited", "Invited"),
        ("Registered", "Registered"),
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("deactivated", "Deactivated"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=15, null=True, blank=True ) 

    is_google_user = models.BooleanField(default=False)
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True
    )
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank="employee")
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    # HRMS Extracted Fields
    manager = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_employees")
    employment_type = models.CharField(max_length=50, default="full_time")
    salary_annual = models.FloatField(default=0.0)
    salary_currency = models.CharField(max_length=10, default="INR")
    skills = models.JSONField(default=list)
    age = models.IntegerField(default=0, null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True, null=True) # or sex
    offboard_date = models.DateField(null=True, blank=True)
    offboard_reason = models.TextField(null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    
    invite_status = models.CharField(
        max_length=20, choices=INVITE_STATUS, default="invited"
    )
    password_reset_required = models.BooleanField(default=True)

    email_otp = models.CharField(max_length=5, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    phone_otp = models.CharField(max_length=5, blank=True, null=True)
    phone_otp_expires_at = models.DateTimeField(blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    reset_token = models.UUIDField(null=True, blank=True)
    token_created_at = models.DateTimeField(null=True, blank=True)
    credits = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    dob = models.CharField(max_length=20, blank=True, null=True)
    height_cm = models.FloatField(default=0.0)
    weight_kg = models.FloatField(default=0.0)
    ethnicity = models.CharField(max_length=50, blank=True, null=True)
    franchise = models.CharField(max_length=100, blank=True, null=True)
    sex = models.CharField(max_length=1, blank=True, null=True) # M, F, O
    managed_conditions = models.JSONField(default=list)
    adherence_pct = models.FloatField(default=75.0)
    is_demo = models.BooleanField(default=False)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class EmployeePlan(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    assigned_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

class Challenge(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("expired", "Expired"),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)             # Bug 4 fix: used by views_employee
    reward = models.CharField(max_length=255, blank=True)  # made optional for seeded challenges
    rules = models.TextField(blank=True)                   # made optional for seeded challenges
    target_value = models.PositiveIntegerField(default=100)  # Bug 4 fix: used by views_employee
    reward_credits = models.PositiveIntegerField(default=0)  # Bug 4 fix: used by views_employee

    start_date = models.DateField(null=True, blank=True)   # made optional for seeded challenges
    end_date = models.DateField(null=True, blank=True)

    challenge_type = models.CharField(max_length=100, blank=True)  # ex: AgeReboot-TN

    departments = models.ManyToManyField(Department, blank=True)
    locations = models.ManyToManyField(Location, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ChallengeParticipant(models.Model):
    STATUS_CHOICES = (
        ("joined", "Joined"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, null=True, blank=True)
    wellness_programme = models.ForeignKey('WellnessProgramme', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    progress = models.PositiveIntegerField(default=0)  # %
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="joined")

    joined_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Note: We keep unique_together but it might need to vary for wellness_programme too.
        # Actually, let's leave it as is or expand it if needed for programmes.
        pass

class Question(models.Model):
    QUESTION_TYPES = (
        ("single_choice", "Single Choice"),
        ("number", "Number"),
        ("date", "Date"),
        ("slider", "Slider"),
    )

    text = models.CharField(max_length=255)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    order = models.PositiveIntegerField()
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return self.text

class QuestionOption(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="options"
    )
    label = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.question.text} - {self.label}"


class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    # for single choice
    selected_option = models.ForeignKey(
        QuestionOption, null=True, blank=True, on_delete=models.SET_NULL
    )

    # for number / slider
    answer_number = models.FloatField(null=True, blank=True)

    # for date
    answer_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "question")

class CreditTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ("reward", "Reward"),
        ("purchase", "Purchase"),
        ("deduction", "Deduction"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="credit_transactions")
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.IntegerField()
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.type} - {self.amount}"



# ──────────────────────────────────────────────
# 1.  Biomarker catalogue  (replaces BIOMARKER_DEFINITIONS dict)
# ──────────────────────────────────────────────

class BiomarkerDefinition(models.Model):
    DIRECTION_CHOICES = [
        ("lower_better",   "Lower is Better"),
        ("higher_better",  "Higher is Better"),
        ("optimal_range",  "Optimal Range"),
    ]
    DATA_SOURCE_CHOICES = [
        ("manual",   "Manual"),
        ("wearable", "Wearable"),
        ("lab",      "Lab"),
    ]

    code         = models.CharField(max_length=60, unique=True)   # e.g. "hba1c"
    name         = models.CharField(max_length=120)
    domain       = models.CharField(max_length=120, blank=True)
    pillar       = models.CharField(max_length=20)                # e.g. "MH", "SR", "CA"
    unit         = models.CharField(max_length=30, blank=True)
    direction    = models.CharField(max_length=20, choices=DIRECTION_CHOICES,
                                    default="optimal_range")
    optimal_low  = models.FloatField(null=True, blank=True)
    optimal_high = models.FloatField(null=True, blank=True)
    longevity_low = models.FloatField(null=True, blank=True)
    longevity_high = models.FloatField(null=True, blank=True)
    data_source  = models.CharField(max_length=20, choices=DATA_SOURCE_CHOICES,
                                    default="manual")

    class Meta:
        ordering = ["pillar", "code"]

    def __str__(self):
        return f"{self.code} – {self.name}"


# ──────────────────────────────────────────────
# 2.  Pillar configuration  (replaces PILLAR_CONFIG dict)
# ──────────────────────────────────────────────

class PillarConfig(models.Model):
    code  = models.CharField(max_length=20, unique=True)   # e.g. "MH"
    name  = models.CharField(max_length=80)
    color = models.CharField(max_length=10, default="#7B35D8")

    def __str__(self):
        return f"{self.code} – {self.name}"


# ──────────────────────────────────────────────
# 3.  Biomarker results  (time-series store)
# ──────────────────────────────────────────────

class BiomarkerResult(models.Model):
    SOURCE_CHOICES = [
        ("MANUAL",           "Manual"),
        ("VALIDATED_MANUAL", "Validated Manual"),
        ("LAB",              "Lab"),
        ("LAB_OCR",          "Lab OCR"),
        ("OCR_EXTRACT",      "OCR Extract"),
        ("WEARABLE",         "Wearable"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name="biomarker_results")
    biomarker    = models.ForeignKey(BiomarkerDefinition, on_delete=models.PROTECT,
                                     to_field="code", db_column="biomarker_code")
    value        = models.FloatField()
    source       = models.CharField(max_length=60, choices=SOURCE_CHOICES, default="MANUAL")
    collected_at = models.DateTimeField()
    ingested_at  = models.DateTimeField(auto_now_add=True)
    validated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="validated_results")

    class Meta:
        ordering = ["-collected_at"]
        indexes  = [
            models.Index(fields=["user", "biomarker", "-collected_at"]),
        ]

    def __str__(self):
        return f"{self.user} | {self.biomarker_id} = {self.value}"


# ──────────────────────────────────────────────
# 4.  Manual entry  (pending clinician validation)
# ──────────────────────────────────────────────

class ManualEntry(models.Model):
    SYSTEM_FLAG_CHOICES = [
        ("normal",              "Normal"),
        ("flagged_out_of_range","Flagged Out of Range"),
    ]
    CLINICIAN_CHOICES = [
        ("pending",  "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    STATUS_CHOICES = [
        ("pending_validation", "Pending Validation"),
        ("validated",          "Validated"),
        ("rejected",           "Rejected"),
    ]

    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user                 = models.ForeignKey(User, on_delete=models.CASCADE,
                                             related_name="manual_entries")
    biomarker            = models.ForeignKey(BiomarkerDefinition, on_delete=models.PROTECT,
                                             to_field="code", db_column="biomarker_code")
    value                = models.FloatField()
    notes                = models.TextField(blank=True)
    entered_by           = models.CharField(max_length=120)
    entered_by_role      = models.CharField(max_length=50, default="employee")
    system_validation    = models.CharField(max_length=30, choices=SYSTEM_FLAG_CHOICES,
                                            default="normal")
    clinician_validation = models.CharField(max_length=20, choices=CLINICIAN_CHOICES,
                                            default="pending")
    clinician            = models.ForeignKey(User, on_delete=models.SET_NULL,
                                             null=True, blank=True,
                                             related_name="clinician_entries")
    clinician_notes      = models.TextField(blank=True)
    status               = models.CharField(max_length=30, choices=STATUS_CHOICES,
                                            default="pending_validation")
    created_at           = models.DateTimeField(auto_now_add=True)
    validated_at         = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} | {self.biomarker_id} ({self.status})"


# ──────────────────────────────────────────────
# 5.  Biomarker correlation catalogue
# ──────────────────────────────────────────────

class BiomarkerCorrelation(models.Model):
    DIRECTION_CHOICES = [
        ("positive", "Positive"),
        ("negative", "Negative"),
    ]
    STRENGTH_CHOICES = [
        ("weak",     "Weak"),
        ("moderate", "Moderate"),
        ("strong",   "Strong"),
    ]

    biomarker_a = models.ForeignKey(BiomarkerDefinition, on_delete=models.CASCADE,
                                    related_name="correlations_as_a", to_field="code",
                                    db_column="biomarker_a_code")
    biomarker_b = models.ForeignKey(BiomarkerDefinition, on_delete=models.CASCADE,
                                    related_name="correlations_as_b", to_field="code",
                                    db_column="biomarker_b_code")
    strength    = models.FloatField()           # 0.0 – 1.0
    direction   = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    insight     = models.TextField()

    class Meta:
        unique_together = ("biomarker_a", "biomarker_b")

    def __str__(self):
        return f"{self.biomarker_a_id} ↔ {self.biomarker_b_id} ({self.direction})"


# ──────────────────────────────────────────────
# 6.  Wearable devices & connections
# ──────────────────────────────────────────────

class WearableDevice(models.Model):
    CATEGORY_CHOICES = [
        ("phone", "Phone"),
        ("ring",  "Ring"),
        ("watch", "Watch"),
        ("band",  "Band"),
        ("scale", "Scale"),
    ]

    device_id = models.CharField(max_length=60, unique=True)  # e.g. "oura"
    name      = models.CharField(max_length=100)
    category  = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    auth_url  = models.URLField(blank=True)
    scope     = models.CharField(max_length=255, blank=True)
    icon      = models.CharField(max_length=40, blank=True)
    metrics   = models.JSONField(default=list)               # ["Heart Rate", "HRV", …]

    def __str__(self):
        return self.name


class WearableConnection(models.Model):
    STATUS_CHOICES = [
        ("active",       "Active"),
        ("disconnected", "Disconnected"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name="wearable_connections")
    device      = models.ForeignKey(WearableDevice, on_delete=models.CASCADE,
                                    to_field="device_id", db_column="device_id")
    connected_at= models.DateTimeField(auto_now_add=True)
    last_sync   = models.DateTimeField(null=True, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    mode        = models.CharField(max_length=20, default="simulated")
    metrics_enabled = models.JSONField(default=list)

    class Meta:
        unique_together = ("user", "device")

    def __str__(self):
        return f"{self.user} – {self.device_id}"


# ──────────────────────────────────────────────
# 7.  Cognitive assessments
# ──────────────────────────────────────────────

class CognitiveAssessmentTemplate(models.Model):
    """Stores PHQ-9, GAD-7, PSQI, DASS-21, MoCA templates."""
    code        = models.CharField(max_length=20, unique=True)
    name        = models.CharField(max_length=120)
    domain      = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    scoring     = models.TextField(blank=True)
    questions   = models.JSONField(default=list)   # list of question strings
    options     = models.JSONField(default=list)   # list of option strings
    max_score   = models.IntegerField()
    pillar      = models.CharField(max_length=20)
    reference   = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class CognitiveAssessmentResult(models.Model):
    SEVERITY_CHOICES = [
        ("normal",   "Normal"),
        ("mild",     "Mild"),
        ("moderate", "Moderate"),
        ("severe",   "Severe"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user            = models.ForeignKey(User, on_delete=models.CASCADE,
                                        related_name="cognitive_results")
    template        = models.ForeignKey(CognitiveAssessmentTemplate, on_delete=models.PROTECT,
                                        to_field="code", db_column="assessment_code")
    answers         = models.JSONField(default=list)
    total_score     = models.IntegerField()
    max_score       = models.IntegerField()
    percentage      = models.FloatField()
    severity        = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    completed_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user} | {self.template_id} ({self.severity})"


# ──────────────────────────────────────────────
# 8.  Report repository
# ──────────────────────────────────────────────

class ReportRepository(models.Model):
    REPORT_TYPE_CHOICES = [
        ("blood_panel", "Blood Panel"),
        ("metabolic",   "Metabolic"),
        ("lipid",       "Lipid"),
        ("hormone",     "Hormone"),
        ("vitamin",     "Vitamin"),
        ("cbc",         "CBC"),
        ("lab_report",  "Lab Report"),
        ("other",       "Other"),
    ]
    PRIVACY_CHOICES = [
        ("private", "Private"),
        ("shared",  "Shared"),
    ]

    id                   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user                 = models.ForeignKey(User, on_delete=models.CASCADE,
                                             related_name="report_repository")
    report_type          = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES,
                                            default="other")
    title                = models.CharField(max_length=200)
    is_hps_report        = models.BooleanField(default=False)
    uploaded_by          = models.CharField(max_length=120)
    uploaded_by_role     = models.CharField(max_length=50, default="employee")
    uploaded_at          = models.DateTimeField(auto_now_add=True)
    report_date          = models.DateTimeField(null=True, blank=True)
    content_preview      = models.TextField(blank=True)
    size_bytes           = models.IntegerField(default=0)
    privacy_level        = models.CharField(max_length=20, choices=PRIVACY_CHOICES,
                                            default="private")
    parameters_extracted = models.IntegerField(default=0)
    extracted_parameters = models.JSONField(default=list)   # list of param dicts

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.user} – {self.title}"


# ──────────────────────────────────────────────
# 8.1. Lab Ingestion — OCR Report tracking
# ──────────────────────────────────────────────

class LabIngestionReport(models.Model):
    id                     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient               = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lab_ingestion_reports")
    lab_partner           = models.CharField(max_length=120, default="MedPlus")
    report_type           = models.CharField(max_length=60, default="blood_panel")
    pdf_url               = models.CharField(max_length=255, blank=True)
    ocr_status            = models.CharField(max_length=30, default="completed")
    extracted_values      = models.JSONField(default=list)
    validation_issues     = models.JSONField(default=list)
    needs_review          = models.BooleanField(default=False)
    review_status         = models.CharField(max_length=30, default="pending")
    ingested_to_biomarkers= models.BooleanField(default=False)
    uploaded_at           = models.DateTimeField(default=timezone.now)
    processed_at          = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"OCR Report {str(self.id)[:8]} for {self.patient.username}"


# ──────────────────────────────────────────────

# 9.  HPS Scores & Health Analytics
# ──────────────────────────────────────────────

class HPSScore(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hps_scores")
    timestamp = models.DateTimeField(default=timezone.now)
    hps_final = models.FloatField()
    hps_base = models.FloatField()
    pillars = models.JSONField(default=dict)
    improvement_bonus = models.FloatField(default=0.0)
    compliance_multiplier = models.FloatField(default=1.0)
    coverage_ratio = models.FloatField(default=1.0)
    ccm = models.FloatField(default=1.0)
    confidence_interval = models.JSONField(default=dict)
    n_metrics_tested = models.IntegerField(default=0)
    tier = models.CharField(max_length=50)
    alert = models.CharField(max_length=150, blank=True, null=True)
    algorithm_version = models.CharField(max_length=20)
    metric_scores = models.JSONField(default=dict)
    raw_values = models.JSONField(default=dict)
    audit_hash = models.CharField(max_length=255)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} - HPS: {self.hps_final} ({self.timestamp.date()})"


# ──────────────────────────────────────────────
# 10. Customer Support / Ticketing
# ──────────────────────────────────────────────

class SupportTicket(models.Model):
    id = models.CharField(primary_key=True, max_length=50) # e.g. TKT-00001
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_tickets", null=True, blank=True)
    user_name = models.CharField(max_length=255)
    user_email = models.EmailField()
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    priority = models.CharField(max_length=50)
    status = models.CharField(max_length=50, default="open")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="assigned_tickets")
    assigned_name = models.CharField(max_length=255, blank=True, null=True)
    escalation_level = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.id} - {self.subject}"


# ──────────────────────────────────────────────
# 11. Care Coordination (CC) Module
# ──────────────────────────────────────────────

class CCAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cc_assignments")
    cc = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assigned_members")
    role = models.CharField(max_length=50) # longevity_physician, fitness_coach, etc.
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.username} -> {self.cc.username} ({self.role})"


class CCAlert(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cc_alerts")
    cc = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_alerts")
    alert_type = models.CharField(max_length=100)
    biomarker = models.CharField(max_length=100, blank=True, null=True)
    value = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    severity = models.CharField(max_length=50)
    threshold = models.FloatField(null=True, blank=True)
    direction = models.CharField(max_length=10, blank=True, null=True)
    ai_interpretation = models.TextField(blank=True, null=True)
    aps_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=50, default="open")
    sla_hours = models.IntegerField(default=24)
    resolution_notes = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_alerts")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CCSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cc = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cc_sessions")
    cc_name = models.CharField(max_length=255)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="member_sessions")
    session_type = models.CharField(max_length=100)
    scheduled_at = models.DateTimeField()
    duration_min = models.IntegerField(default=30)
    status = models.CharField(max_length=50, default="scheduled")
    notes = models.TextField(blank=True, null=True)
    action_items = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CCProtocol(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lgp_id = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100)
    evidence_grade = models.CharField(max_length=50)
    intervention_type = models.CharField(max_length=100)
    duration_weeks = models.IntegerField(default=12)
    expected_outcomes = models.JSONField(default=list)
    hps_dimensions = models.JSONField(default=list)
    impact_scores = models.JSONField(default=dict)
    contraindications = models.JSONField(default=list)
    drug_interactions = models.JSONField(default=list)
    smart_goals_template = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class CCPrescription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cc_prescriptions")
    clinician = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prescribed_protocols")
    protocol = models.ForeignKey(CCProtocol, on_delete=models.CASCADE)
    protocol_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    duration_weeks = models.IntegerField(default=12)
    custom_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default="active")
    prescribed_at = models.DateTimeField(auto_now_add=True)
    evidence_grade = models.CharField(max_length=10, blank=True, null=True)



class CarePlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="care_plans")
    hcp = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_care_plans")
    hcp_name = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default="active")
    protocols = models.JSONField(default=list) 
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CCMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_cc_messages")
    sender_name = models.CharField(max_length=255, blank=True)
    sender_role = models.CharField(max_length=50, blank=True)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_cc_messages")
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

class CCOverrideAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hps_overrides")
    clinician = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conducted_overrides")
    clinician_name = models.CharField(max_length=255, blank=True)
    override_type = models.CharField(max_length=100, blank=True)
    dimension = models.CharField(max_length=50, blank=True, null=True)
    old_value = models.FloatField()
    new_value = models.FloatField()
    reason_code = models.CharField(max_length=50)
    reason_text = models.TextField(blank=True)
    requires_dual_approval = models.BooleanField(default=False)
    approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    old_value = models.FloatField(null=True, blank=True)
    new_value = models.FloatField(null=True, blank=True)
    reason_code = models.CharField(max_length=100)
    reason_text = models.TextField()
    requires_dual_approval = models.BooleanField(default=False)
    approved = models.BooleanField(default=True)
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_overrides")
    created_at = models.DateTimeField(auto_now_add=True)


class CCReferral(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referrals")
    member_name = models.CharField(max_length=255)
    referred_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_referrals")
    referred_to_name = models.CharField(max_length=255)
    referral_type = models.CharField(max_length=100)
    reason = models.TextField()
    priority = models.CharField(max_length=50, default="normal")
    status = models.CharField(max_length=50, default="pending")
    referring_clinician = models.ForeignKey(User, on_delete=models.CASCADE, related_name="outgoing_referrals")
    referring_clinician_name = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ──────────────────────────────────────────────
# 11.5. COACHING & WELLNESS MODULES (PFC, PSY, NUT)
# ──────────────────────────────────────────────

class CoachTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="coach_tasks")
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="member_coach_tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="pending") # pending, completed
    priority = models.CharField(max_length=20, default="medium")
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class FitnessProfile(models.Model):
    member = models.OneToOneField(User, on_delete=models.CASCADE, related_name="fitness_profile")
    training_experience = models.CharField(max_length=50, default="intermediate")
    exercise_preferences = models.JSONField(default=list)
    equipment_access = models.JSONField(default=list)
    injury_log = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="updated_fitness_profiles")

class ExerciseProgramme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_programmes")
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exercise_programmes")
    name = models.CharField(max_length=255)
    primary_goal = models.CharField(max_length=100, default="longevity")
    duration_weeks = models.IntegerField(default=12)
    training_days_per_week = models.IntegerField(default=4)
    session_duration_min = models.IntegerField(default=45)
    periodisation = models.CharField(max_length=50, default="block")
    exercises = models.JSONField(default=list)
    progression_rule = models.CharField(max_length=100, default="weekly_pct")
    clinician_protocol = models.TextField(blank=True, null=True)
    hr_zones = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

class ExerciseSessionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    programme = models.ForeignKey(ExerciseProgramme, on_delete=models.SET_NULL, null=True, related_name="session_logs")
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="logged_fitness_sessions")
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fitness_session_logs")
    session_date = models.DateTimeField(default=timezone.now)
    exercises_completed = models.JSONField(default=list)
    session_rpe = models.IntegerField(null=True, blank=True)
    hr_data = models.JSONField(default=dict, blank=True)
    compliance_pct = models.FloatField(default=100.0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CBTModule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    sessions = models.IntegerField(default=8)
    description = models.TextField()
    protocol_id = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CBTAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(CBTModule, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cbt_assignments")
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assigned_cbt_modules")
    status = models.CharField(max_length=20, default="active")
    sessions_completed = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=8)
    homework = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

class TherapyProgram(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="therapy_programs")
    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name="managed_therapy_programs")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100, default="Stress Management")
    duration_weeks = models.IntegerField(default=8)
    sessions_per_week = models.IntegerField(default=1)
    modules = models.JSONField(default=list)
    goals = models.JSONField(default=list)
    status = models.CharField(max_length=20, default="active")
    sessions_completed = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class TherapyNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="therapy_notes")
    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name="written_therapy_notes")
    session_date = models.DateTimeField(default=timezone.now)
    session_type = models.CharField(max_length=50, default="individual")
    subjective = models.TextField(blank=True)
    objective = models.TextField(blank=True)
    assessment = models.TextField(blank=True)
    plan = models.TextField(blank=True)
    risk_assessment = models.CharField(max_length=50, default="none")
    interventions_used = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

class CrisisAlert(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crisis_alerts")
    type = models.CharField(max_length=100, default="suicidal_ideation")
    severity = models.CharField(max_length=20, default="CRITICAL")
    status = models.CharField(max_length=20, default="active")
    detected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="detected_crises")
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class BehaviorLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="behavior_logs")
    date = models.DateField(default=timezone.now)
    mood_score = models.IntegerField(default=5)
    sleep_adherence = models.BooleanField(default=False)
    meditation_done = models.BooleanField(default=False)
    screen_time_hrs = models.FloatField(null=True, blank=True)
    stress_triggers = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

class NutritionalProfile(models.Model):
    member = models.OneToOneField(User, on_delete=models.CASCADE, related_name="nutritional_profile")
    weight_kg = models.FloatField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    activity_level = models.CharField(max_length=50, default="moderate")
    dietary_preferences = models.JSONField(default=list)
    target_kcal = models.IntegerField(null=True, blank=True)
    macros = models.JSONField(default=dict) # protein_g, carb_g, fat_g
    updated_at = models.DateTimeField(auto_now=True)

class MealPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_meal_plans")
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="meal_plans")
    name = models.CharField(max_length=255)
    duration_days = models.IntegerField(default=7)
    target_kcal = models.IntegerField(null=True, blank=True)
    macros = models.JSONField(default=dict)
    meals = models.JSONField(default=list)
    supplements = models.JSONField(default=list)
    status = models.CharField(max_length=20, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

class MealPlanDay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name="days")
    day_number = models.IntegerField()
    meals = models.JSONField(default=dict) # breakfast, lunch, dinner, snacks
    total_calories = models.IntegerField(default=0)
    total_protein = models.IntegerField(default=0)
    total_carbs = models.IntegerField(default=0)
    total_fat = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class NutritionConsultationNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="nutrition_notes")
    nutritionist = models.ForeignKey(User, on_delete=models.CASCADE, related_name="written_nutrition_notes")
    date = models.DateField(default=timezone.now)
    dietary_analysis = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    meal_plan_updates = models.TextField(blank=True)
    supplement_changes = models.TextField(blank=True)
    follow_up_plan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SupplementStack(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="supplement_stacks")
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prescribed_supplements")
    supplements = models.JSONField(default=list)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

class Habit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habits")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    frequency = models.CharField(max_length=50, default="daily")
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="assigned_habits")
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

class HabitLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="logs")
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    completed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CheckIn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="check_ins")
    type = models.CharField(max_length=50, default="weekly")
    mood_rating = models.IntegerField(default=5)
    energy_level = models.IntegerField(default=5)
    sleep_quality = models.IntegerField(default=5)
    stress_level = models.IntegerField(default=5)
    adherence_self_rating = models.IntegerField(default=7)
    coach_notes = models.TextField(blank=True)
    conducted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="conducted_checkins")
    created_at = models.DateTimeField(auto_now_add=True)

class BodyComposition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="body_comps")
    date = models.DateField()
    weight_kg = models.FloatField()
    body_fat_pct = models.FloatField()
    lean_mass_kg = models.FloatField(null=True, blank=True)
    bmi = models.FloatField(null=True, blank=True)
    waist_cm = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Goal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="goals")
    category = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    target_value = models.FloatField(null=True, blank=True)
    current_value = models.FloatField(default=0.0)
    unit = models.CharField(max_length=50, blank=True)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default="active") # active, completed
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_goals")
    created_at = models.DateTimeField(auto_now_add=True)

class ResourceShare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource_id = models.CharField(max_length=50) # e.g. r1, r2
    resource_title = models.CharField(max_length=255)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shared_resources")
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resources_shared_by")
    shared_at = models.DateTimeField(auto_now_add=True)


# ──────────────────────────────────────────────
# 12. EMR, Consultations & Telehealth
# ──────────────────────────────────────────────

class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments")
    member_name = models.CharField(max_length=255)
    appointment_type = models.CharField(max_length=100)
    mode = models.CharField(max_length=100) # physical / telehealth
    scheduled_at = models.DateTimeField()
    duration_min = models.IntegerField(default=30)
    fee_type = models.CharField(max_length=50)
    fee_amount = models.FloatField(default=0.0)
    reason = models.TextField()
    assigned_hcp = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="hcp_appointments")
    assigned_hcp_name = models.CharField(max_length=255)
    is_new_patient = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default="scheduled")
    notes = models.TextField(blank=True, null=True)
    encounter_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MemberMedicalHistory(models.Model):
    member = models.OneToOneField(User, on_delete=models.CASCADE, related_name="medical_history")
    conditions = models.JSONField(default=list)
    family_history = models.JSONField(default=list)
    surgical_history = models.JSONField(default=list)
    personal_history = models.JSONField(default=dict)
    gynaec_history = models.JSONField(default=dict, blank=True, null=True)
    allergies = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)


class VitalsLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vitals_logs")
    vitals = models.JSONField(default=dict)
    recorded_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="recorded_vitals")
    recorded_by_name = models.CharField(max_length=255, blank=True, null=True)


class EMREncounter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emr_encounters")
    hcp = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="conducted_encounters")
    encounter_type = models.CharField(max_length=100)
    chief_complaint = models.TextField(blank=True, null=True)
    subjective = models.TextField(blank=True, null=True)
    objective = models.TextField(blank=True, null=True)
    assessment = models.TextField(blank=True, null=True)
    plan = models.TextField(blank=True, null=True)
    diagnosis_codes = models.JSONField(default=list)
    vitals = models.JSONField(default=dict)
    
    # Linked Entities (Smart Encounter Parity)
    linked_lab_orders = models.JSONField(default=list)
    linked_pharmacy_orders = models.JSONField(default=list)
    linked_referrals = models.JSONField(default=list)
    linked_protocols = models.JSONField(default=list)
    linked_diagnostics = models.JSONField(default=list)
    linked_prescriptions = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)


# ──────────────────────────────────────────────
# 13. Nutrition & Diet
# ──────────────────────────────────────────────

class NutritionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="nutrition_logs")
    date = models.DateField(default=timezone.now)
    meal_type = models.CharField(max_length=50)
    items = models.JSONField(default=list)
    totals = models.JSONField(default=dict)
    foods = models.JSONField(default=list)
    total_calories = models.FloatField(default=0.0)
    logged_at = models.DateTimeField(auto_now_add=True)

class NutritionPlan(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="nutrition_plan")
    plan = models.JSONField(default=dict)
    daily_target = models.JSONField(default=dict)
    goal = models.CharField(max_length=255, blank=True, null=True)
    generated_at = models.DateTimeField(auto_now=True)

# ──────────────────────────────────────────────
# 14. Admin / HRMS / System Models
# ──────────────────────────────────────────────

class PlatformAnnouncement(models.Model):
    ANNOUNCEMENT_TYPES = [
        ('info', 'Info'), ('warning', 'Warning'), ('maintenance', 'Maintenance'), 
        ('feature', 'Feature'), ('critical', 'Critical')
    ]
    TARGET_OPTIONS = [
        ('all', 'All Users'), ('employee', 'Employee'), ('longevity_physician', 'Longevity Physician'),
        ('fitness_coach', 'Fitness Coach'), ('psychologist', 'Psychologist'), 
        ('nutritional_coach', 'Nutritional Coach'), ('corporate_hr_admin', 'Corporate HR Admin'),
        ('corporate_wellness_head', 'Corporate Wellness Head'), ('cxo_executive', 'CXO Executive')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField()
    announcement_type = models.CharField(max_length=50, choices=ANNOUNCEMENT_TYPES, default="info")
    target_role = models.CharField(max_length=50, choices=TARGET_OPTIONS, default="all") # e.g. "hcp", "employee"
    audience_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="announcements")
    is_active = models.BooleanField(default=True)
    is_dismissible = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    action_url = models.URLField(blank=True, null=True)
    action_label = models.CharField(max_length=100, blank=True, null=True)
    dismissed_by = models.ManyToManyField(User, related_name="dismissed_announcements", blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="authored_announcements")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

class PlatformContent(models.Model):
    CONTENT_TYPES = [
        ('health_tip', 'Health Tip'), ('article', 'Article'), ('faq', 'FAQ'),
        ('notification_template', 'Notification Template'), ('onboarding_step', 'Onboarding Step')
    ]
    CONTENT_STATUSES = [
        ('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    body = models.TextField()
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPES, default="health_tip")
    category = models.CharField(max_length=100, blank=True)
    tags = models.JSONField(default=list, blank=True)
    target_roles = models.JSONField(default=list, blank=True) # Array of role names
    status = models.CharField(max_length=20, choices=CONTENT_STATUSES, default="draft")
    featured_image_url = models.URLField(blank=True, null=True)
    
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="authored_platform_content")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-updated_at']

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=255)
    resource = models.CharField(max_length=150)
    details = models.JSONField(default=dict)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
class EmployeeLeave(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=50) # PTO, Sick
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=50, default="pending") # approved, rejected
    reason = models.TextField(blank=True, null=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="managed_leaves")
    created_at = models.DateTimeField(auto_now_add=True)

class PayrollRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payrolls")
    period_start = models.DateField()
    period_end = models.DateField()
    base_salary = models.FloatField()
    bonuses = models.FloatField(default=0.0)
    deductions = models.FloatField(default=0.0)
    net_pay = models.FloatField()
    status = models.CharField(max_length=50, default="processed") # processed, disbursed
    disbursed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class HelpdeskTicket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="helpdesk_tickets")
    subject = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100) # IT, HR, Finance
    priority = models.CharField(max_length=50, default="medium")
    status = models.CharField(max_length=50, default="open")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="assigned_helpdesk")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# ──────────────────────────────────────────────
# 15. Clinical / Pharmacy
# ──────────────────────────────────────────────

class PharmacyCatalogItem(models.Model):
    item_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50) # prescription, nutraceutical
    category = models.CharField(max_length=100)
    requires_rx = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class PharmacyOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=100, unique=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pharmacy_orders")
    ordered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_pharmacy_orders")
    order_type = models.CharField(max_length=50, default="standard")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default="pending") # pending, approved, dispensing, dispensed, shipped, delivered, cancelled
    pharmacy_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    ordered_at = models.DateTimeField(default=timezone.now)
    dispensed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-ordered_at"]

    def __str__(self):
        return f"{self.order_number} ({self.status})"

class PharmacyOrderItem(models.Model):
    order = models.ForeignKey(PharmacyOrder, on_delete=models.CASCADE, related_name="items")
    catalog_item = models.ForeignKey(PharmacyCatalogItem, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=1)
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)
    dosing_instructions = models.TextField(blank=True)

    def __str__(self):
        return f"{self.catalog_item.name} x {self.quantity}"

class PharmacyInventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100) # drug, lab_kit, equipment
    quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = models.CharField(max_length=255, blank=True, null=True)
    last_restocked = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

# ──────────────────────────────────────────────
# 16. Corp / B2B Dashboards
# ──────────────────────────────────────────────

class CompanyContract(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="contracts")
    plan_tier = models.CharField(max_length=100) # enterprise, premium
    start_date = models.DateField()
    end_date = models.DateField()
    max_employees = models.IntegerField(default=100)
    pricing_model = models.CharField(max_length=100) # per_seat, flat_fee
    is_active = models.BooleanField(default=True)

class PlatformStat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(default=timezone.now)
    metric_name = models.CharField(max_length=100)
    metric_value = models.FloatField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name="stats")
    
# ──────────────────────────────────────────────
# 17. CXO / Strategic
# ──────────────────────────────────────────────

class StrategicObjective(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=100)
    target_metric = models.CharField(max_length=100)
    target_value = models.FloatField()
    current_value = models.FloatField(default=0.0)
    deadline = models.DateField()
    status = models.CharField(max_length=50, default="on_track") # on_track, behind, achieved
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="strategic_objectives")
    updated_at = models.DateTimeField(auto_now=True)

# ──────────────────────────────────────────────
# 18. HRMS / Asset Tracking
# ──────────────────────────────────────────────

class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_tag = models.CharField(max_length=50, unique=True)
    asset_type = models.CharField(max_length=50) # laptop, monitor, etc.
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=150, blank=True)
    purchase_date = models.CharField(max_length=50, blank=True)
    purchase_cost = models.FloatField(default=0.0)
    warranty_expiry = models.CharField(max_length=50, blank=True)
    
    status = models.CharField(max_length=50, default="available") # available, assigned, under_repair, etc.
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_assets")
    assigned_to_name = models.CharField(max_length=255, null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True, null=True)
    history = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.asset_tag} - {self.asset_type}"

class LeaveBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="leave_balance")
    year = models.IntegerField(default=timezone.now().year)
    casual_leave = models.JSONField(default=dict)
    sick_leave = models.JSONField(default=dict)
    earned_leave = models.JSONField(default=dict)
    comp_off = models.JSONField(default=dict)

# ── Corporate Intelligence Models (B2B Dashboard) ──────────────────────────

class EHSScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ehs_scores")
    score = models.FloatField()
    tier = models.CharField(max_length=50)
    timestamp = models.DateTimeField(default=timezone.now)

class BRIScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bri_scores")
    score = models.FloatField()
    tier = models.CharField(max_length=50) # green, yellow, orange, red
    physiological = models.FloatField(default=0)
    behavioural = models.FloatField(default=0)
    psychological = models.FloatField(default=0)
    organisational = models.FloatField(default=0)
    timestamp = models.DateTimeField(default=timezone.now)

class CorpBiomarkerResult(models.Model):
    """Lightweight biomarker snapshot for corporate analytics (distinct from the full BiomarkerResult above)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="corp_biomarkers")
    biomarker_name = models.CharField(max_length=100)
    value = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=20, null=True, blank=True)
    ingested_at = models.DateTimeField(default=timezone.now)
    observed_at = models.DateTimeField(null=True, blank=True)

class CorpWearableConnection(models.Model):
    """Simplified wearable flag for corporate dashboards (distinct from the full WearableConnection above)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="corp_wearable")
    connected = models.BooleanField(default=False)
    device_type = models.CharField(max_length=100, null=True, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)

class LabPartner(models.Model):
    id = models.CharField(max_length=50, primary_key=True) # e.g. LP-THY
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50) # reference_lab, in_house
    tat_modifier = models.IntegerField(default=0)
    accreditation = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name

class LabPanel(models.Model):
    panel_id        = models.CharField(max_length=100, primary_key=True)
    name            = models.CharField(max_length=255)
    category        = models.CharField(max_length=100, blank=True)
    description     = models.TextField(blank=True)
    tests_included  = models.JSONField(default=list)
    price           = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    turnaround_time = models.CharField(max_length=50, blank=True)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class LabOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=100, unique=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lab_orders")
    ordered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_lab_orders")
    panel = models.ForeignKey(LabPanel, on_delete=models.PROTECT, related_name="orders")
    lab_partner = models.ForeignKey(LabPartner, on_delete=models.PROTECT, related_name="orders")
    priority = models.CharField(max_length=20, default="routine")
    fasting_required = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default="ordered")
    notes = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    turnaround_days = models.IntegerField(default=1)
    
    # Specimen details (Matching Flask)
    specimen_type = models.CharField(max_length=50, default="blood")
    specimen_collected = models.BooleanField(default=False)
    specimen_barcode = models.CharField(max_length=100, blank=True)
    specimen_transport_status = models.CharField(max_length=50, default="pending")
    
    ordered_at = models.DateTimeField(default=timezone.now)
    collected_at = models.DateTimeField(null=True, blank=True)
    processing_at = models.DateTimeField(null=True, blank=True)
    resulted_at = models.DateTimeField(null=True, blank=True)
    
    results = models.JSONField(default=list)
    result_notes = models.TextField(blank=True)
    abnormal_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-ordered_at"]

    def __str__(self):
        return f"{self.order_number} ({self.status})"

class NudgeCampaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    segment_id = models.CharField(max_length=100)
    segment_label = models.CharField(max_length=100)
    message_template = models.TextField()
    channel = models.CharField(max_length=50, default="in_app")
    target_count = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    delivered_count = models.IntegerField(default=0)
    opened_count = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="draft")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)

class HREscalation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=100)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hr_escalations")
    reason = models.TextField()
    recommended_action = models.TextField(null=True, blank=True)
    severity = models.CharField(max_length=50, default="medium")
    status = models.CharField(max_length=50, default="pending")
    manager_response = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_hr_escalations")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

class CareTeamEscalation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="care_escalations")
    type = models.CharField(max_length=100)
    reason = models.TextField()
    urgency = models.CharField(max_length=50, default="normal")
    status = models.CharField(max_length=50, default="pending")
    escalated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="escalated_care")
    created_at = models.DateTimeField(default=timezone.now)

class WellnessProgramme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, default="challenge")
    target_dimension = models.CharField(max_length=100)
    duration_days = models.IntegerField(default=30)
    status = models.CharField(max_length=50, default="upcoming")
    enrolled = models.IntegerField(default=0)
    completed = models.IntegerField(default=0)
    reward_healthcoins = models.IntegerField(default=500)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)

class Intervention(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="interventions")
    type = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=50, default="active")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="assigned_interventions")
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_interventions")
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    outcome = models.TextField(null=True, blank=True)

class FranchiseSeason(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default="upcoming")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    qualification_hps = models.IntegerField(default=550)
    qualification_pct_required = models.IntegerField(default=60)
    reward_pool_inr = models.IntegerField(default=5000000)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)


# ══════════════════════════════════════════════════════════════════
# §  MIGRATED FROM FLASK/FASTAPI (MongoDB → SQLite)
# All collections from the original FastAPI project are represented
# below as relational Django models.
# ══════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────
# 19. Social Feed
# ──────────────────────────────────────────────

class SocialPost(models.Model):
    """Maps to mongo: db.social_feed"""
    POST_TYPE_CHOICES = [
        ("post",      "Post"),
        ("achievement", "Achievement"),
        ("challenge", "Challenge"),
        ("milestone", "Milestone"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_posts")
    post_type    = models.CharField(max_length=30, choices=POST_TYPE_CHOICES, default="post")
    content      = models.TextField()
    photo_id     = models.CharField(max_length=100, blank=True, null=True)
    likes        = models.PositiveIntegerField(default=0)
    liked_by     = models.ManyToManyField(User, related_name="liked_posts", blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} – {self.post_type}"


class SocialComment(models.Model):
    """Comments on a SocialPost."""
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post       = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="comments")
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_comments")
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} on {self.post_id}"


# ──────────────────────────────────────────────
# 20. User Badges
# ──────────────────────────────────────────────

class UserBadge(models.Model):
    """Maps to mongo: db.user_badges"""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="badges")
    badge_code   = models.CharField(max_length=60)
    challenge    = models.ForeignKey(
        "Challenge", on_delete=models.SET_NULL, null=True, blank=True, related_name="badges_awarded"
    )
    earned_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge_code")

    def __str__(self):
        return f"{self.user.username} – {self.badge_code}"


# ──────────────────────────────────────────────
# 21. Credit Balance  (wallet; individual transactions → CreditTransaction)
# ──────────────────────────────────────────────

class CreditBalance(models.Model):
    """Maps to mongo: db.credits  (one record per user, tracks totals)"""
    user      = models.OneToOneField(User, on_delete=models.CASCADE, related_name="credit_balance")
    available = models.IntegerField(default=0)
    purchased = models.IntegerField(default=0)
    consumed  = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} – {self.available} credits"


# ──────────────────────────────────────────────
# 22. Notifications
# ──────────────────────────────────────────────

class Notification(models.Model):
    """Maps to mongo: db.notifications"""
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type       = models.CharField(max_length=80)  # protocol_approved, referral_created, …
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    data       = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} – {self.type}"


# ──────────────────────────────────────────────
# 23. WhatsApp Notification Logs
# ──────────────────────────────────────────────

class WhatsappLog(models.Model):
    """Maps to mongo: db.whatsapp_logs"""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="whatsapp_logs")
    phone        = models.CharField(max_length=20)
    message_type = models.CharField(max_length=60)   # alert, reminder, report, etc.
    content      = models.TextField(blank=True)
    status       = models.CharField(max_length=30, default="sent")  # sent / failed / delivered
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone} – {self.message_type} ({self.status})"


# ──────────────────────────────────────────────
# 24. Video Consultations
# ──────────────────────────────────────────────

class VideoConsultation(models.Model):
    """Maps to mongo: db.video_consultations"""
    STATUS_CHOICES = [
        ("scheduled",   "Scheduled"),
        ("in_progress", "In Progress"),
        ("completed",   "Completed"),
        ("cancelled",   "Cancelled"),
        ("no_show",     "No Show"),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="video_consultations")
    doctor           = models.ForeignKey("CareTeamMember", on_delete=models.SET_NULL, null=True,
                                         related_name="video_consultations")
    doctor_name      = models.CharField(max_length=255)
    scheduled_at     = models.DateTimeField()
    duration_min     = models.IntegerField(default=30)
    reason           = models.TextField(blank=True)
    status           = models.CharField(max_length=30, choices=STATUS_CHOICES, default="scheduled")
    room_id          = models.CharField(max_length=100, blank=True, null=True)
    room_name        = models.CharField(max_length=100, blank=True, null=True)
    recording_url    = models.URLField(blank=True, null=True)
    chat_messages    = models.JSONField(default=list)   # in-session chat
    panels_ordered   = models.JSONField(default=list)
    biomarkers_ordered = models.JSONField(default=list)
    emr_data         = models.JSONField(default=dict, blank=True)
    consultation_summary = models.TextField(blank=True)
    emr_encounter    = models.ForeignKey("EMREncounter", on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name="video_consultations")
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"{self.patient.username} ↔ {self.doctor_name} ({self.status})"


# ──────────────────────────────────────────────
# 25. Telehealth Sessions  (async / non-video)
# ──────────────────────────────────────────────

class TelehealthSession(models.Model):
    """Maps to mongo: db.telehealth_sessions"""
    SESSION_TYPE_CHOICES = [
        ("video",    "Video"),
        ("audio",    "Audio"),
        ("chat",     "Chat"),
        ("async",    "Async"),
    ]
    STATUS_CHOICES = [
        ("scheduled",   "Scheduled"),
        ("in_progress", "In Progress"),
        ("completed",   "Completed"),
        ("cancelled",   "Cancelled"),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="telehealth_sessions")
    hcp           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                       related_name="hcp_telehealth_sessions")
    hcp_name      = models.CharField(max_length=255, blank=True)
    session_type  = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default="video")
    scheduled_at  = models.DateTimeField()
    duration_min  = models.IntegerField(default=30)
    reason        = models.TextField(blank=True)
    status        = models.CharField(max_length=30, choices=STATUS_CHOICES, default="scheduled")
    room_url      = models.URLField(blank=True, null=True)
    chat_messages = models.JSONField(default=list)
    notes         = models.TextField(blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"{self.member.username} – {self.session_type} ({self.status})"


# ──────────────────────────────────────────────
# 26. Phlebotomists & Sample Bookings
# ──────────────────────────────────────────────

class Phlebotomist(models.Model):
    """Maps to mongo: db.phlebotomists"""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name="phlebotomist_profile")
    name         = models.CharField(max_length=255)
    phone        = models.CharField(max_length=20)
    zone         = models.CharField(max_length=100, blank=True)
    city         = models.CharField(max_length=100, blank=True)
    status       = models.CharField(max_length=30, default="active")  # active / off_duty
    latitude     = models.FloatField(null=True, blank=True)
    longitude    = models.FloatField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.zone})"


class SampleBooking(models.Model):
    """Maps to mongo: db.sample_bookings"""
    STATUS_CHOICES = [
        ("pending",    "Pending"),
        ("assigned",   "Assigned"),
        ("en_route",   "En Route"),
        ("collected",  "Collected"),
        ("cancelled",  "Cancelled"),
    ]

    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient               = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sample_bookings")
    lab_order             = models.ForeignKey("LabOrder", on_delete=models.SET_NULL, null=True, blank=True,
                                              related_name="sample_bookings")
    panel_ids             = models.JSONField(default=list)
    preferred_date        = models.DateField()
    preferred_slot        = models.CharField(max_length=50)
    address_type          = models.CharField(max_length=20, default="home")
    address_line          = models.CharField(max_length=255, blank=True)
    landmark              = models.CharField(max_length=255, blank=True)
    city                  = models.CharField(max_length=100, blank=True)
    pincode               = models.CharField(max_length=10, blank=True)
    fasting_confirmed     = models.BooleanField(default=False)
    special_instructions  = models.TextField(blank=True)
    status                = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    assigned_phlebotomist = models.ForeignKey(Phlebotomist, on_delete=models.SET_NULL,
                                              null=True, blank=True, related_name="assigned_bookings")
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient.username} – {self.preferred_date} ({self.status})"


class PhlebotomistJob(models.Model):
    """Maps to mongo: db.phlebotomist_jobs  (route-optimised job assignments)"""
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phlebotomist   = models.ForeignKey(Phlebotomist, on_delete=models.CASCADE, related_name="jobs")
    booking        = models.ForeignKey(SampleBooking, on_delete=models.CASCADE, related_name="job")
    route_order    = models.PositiveIntegerField(default=0)
    eta_minutes    = models.IntegerField(null=True, blank=True)
    status         = models.CharField(max_length=30, default="pending")
    assigned_at    = models.DateTimeField(auto_now_add=True)
    completed_at   = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.phlebotomist.name} → booking {self.booking_id}"


# ──────────────────────────────────────────────
# 27. Roadmaps & Roadmap Reviews
# ──────────────────────────────────────────────

class Roadmap(models.Model):
    """Maps to mongo: db.roadmaps  (AI health roadmap per user)"""
    STATUS_CHOICES = [
        ("active",    "Active"),
        ("completed", "Completed"),
        ("archived",  "Archived"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roadmaps")
    title       = models.CharField(max_length=255, default="My Health Roadmap")
    goals       = models.JSONField(default=list)
    milestones  = models.JSONField(default=list)
    phases      = models.JSONField(default=list)
    ai_summary  = models.TextField(blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} – Roadmap ({self.status})"


class RoadmapReview(models.Model):
    """Maps to mongo: db.roadmap_reviews"""
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    roadmap     = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="reviews")
    reviewer    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name="roadmap_reviews")
    hps_at_review = models.FloatField(null=True, blank=True)
    notes       = models.TextField(blank=True)
    goals_achieved = models.JSONField(default=list)
    next_steps  = models.JSONField(default=list)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review of roadmap {self.roadmap_id}"


# ──────────────────────────────────────────────
# 28. Longevity Protocols  (AI-generated patient plans)
# ──────────────────────────────────────────────

class LongevityProtocol(models.Model):
    """Maps to mongo: db.longevity_protocols"""
    STATUS_CHOICES = [
        ("pending_review", "Pending Review"),
        ("approved",       "Approved"),
        ("modified",       "Modified"),
        ("rejected",       "Rejected"),
    ]

    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient               = models.ForeignKey(User, on_delete=models.CASCADE,
                                              related_name="longevity_protocols")
    patient_name          = models.CharField(max_length=255)
    generated_by          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                              related_name="generated_protocols")
    generated_by_name     = models.CharField(max_length=255, blank=True)
    hps_at_generation     = models.FloatField(default=0.0)
    # phased plan (AI output stored as JSON)
    three_month_plan      = models.JSONField(default=list)
    six_month_plan        = models.JSONField(default=list)
    nine_month_plan       = models.JSONField(default=list)
    daily_challenges      = models.JSONField(default=list)
    weekly_goals          = models.JSONField(default=list)
    ai_generated          = models.BooleanField(default=True)
    # doctor review
    status                = models.CharField(max_length=30, choices=STATUS_CHOICES,
                                             default="pending_review")
    doctor_notes          = models.TextField(blank=True)
    doctor_modifications  = models.JSONField(default=list)
    approved_by           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                              related_name="approved_protocols")
    approved_by_name      = models.CharField(max_length=255, blank=True)
    approved_at           = models.DateTimeField(null=True, blank=True)
    delivered_to_patient  = models.BooleanField(default=False)
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient_name} – Protocol ({self.status})"


# ──────────────────────────────────────────────
# 29. Referrals
# ──────────────────────────────────────────────

class Referral(models.Model):
    """Maps to mongo: db.referrals (legacy EMR transitions of care)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="legacy_referrals", null=True, blank=True)
    member_name = models.CharField(max_length=255, blank=True, null=True)
    referred_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="legacy_outgoing_referrals")
    referred_by_name = models.CharField(max_length=255, blank=True, null=True)
    referred_to_role = models.CharField(max_length=100, blank=True, null=True)
    referred_to_id = models.CharField(max_length=100, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default="pending", null=True, blank=True)
    encounter_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Referral for {self.member_name} – {self.status}"



# ──────────────────────────────────────────────



# ──────────────────────────────────────────────
# 30. Care Plans  (structured patient care plans)
# ──────────────────────────────────────────────



class CarePlanGoal(models.Model):
    """Individual goal within a CarePlan."""
    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("achieved",    "Achieved"),
        ("missed",      "Missed"),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    care_plan     = models.ForeignKey('CarePlan', on_delete=models.CASCADE, related_name="goals")
    description   = models.TextField()
    target_value  = models.CharField(max_length=100, blank=True)
    current_value = models.CharField(max_length=100, blank=True)
    due_date      = models.DateField(null=True, blank=True)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_started")
    updated_at    = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.care_plan} → Goal: {self.description[:50]}"


# ──────────────────────────────────────────────
# 31. Care Teams  (user's personal care-team roster)
# ──────────────────────────────────────────────

class CareTeam(models.Model):
    """Maps to mongo: db.care_teams  (the team assigned to a member)"""
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user    = models.OneToOneField(User, on_delete=models.CASCADE, related_name="care_team")
    members = models.JSONField(default=list)   # [{role, name, email, credits_per_session, status}]

    def __str__(self):
        return f"CareTeam of {self.user.username}"


class CareAppointment(models.Model):
    """Maps to mongo: db.care_appointments"""
    STATUS_CHOICES = [
        ("confirmed",  "Confirmed"),
        ("completed",  "Completed"),
        ("cancelled",  "Cancelled"),
        ("no_show",    "No Show"),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name="care_appointments")
    member_name      = models.CharField(max_length=255)
    member_role      = models.CharField(max_length=100)
    member_index     = models.PositiveIntegerField(default=0)
    date             = models.DateField()
    time             = models.CharField(max_length=20)
    reason           = models.TextField(blank=True)
    appointment_type = models.CharField(max_length=50, default="consultation")
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default="confirmed")
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.username} with {self.member_name} on {self.date}"


class CareReview(models.Model):
    """Maps to mongo: db.care_reviews  (ratings for care team members)"""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="care_reviews")
    member_index = models.PositiveIntegerField(default=0)
    member_name  = models.CharField(max_length=255)
    member_role  = models.CharField(max_length=100)
    rating       = models.PositiveSmallIntegerField()   # 1-5
    nps_score    = models.SmallIntegerField(default=0)  # 0-10
    review_text  = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} – {self.rating}/5 for {self.member_name}"


# ──────────────────────────────────────────────
# 32. Mental Health Assessments
# ──────────────────────────────────────────────

class MentalAssessment(models.Model):
    """Maps to mongo: db.mental_assessments"""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mental_assessments")
    answers      = models.JSONField(default=list)
    results      = models.JSONField(default=dict)  # {depression:{…}, anxiety:{…}, sleep:{…}, …}
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user.username} – MH Assessment {self.completed_at.date()}"


class CAAssessment(models.Model):
    """Maps to mongo: db.ca_assessments"""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ca_assessments")
    timestamp    = models.DateTimeField(auto_now_add=True)
    data         = models.JSONField(default=dict)
    result       = models.JSONField(default=dict)
    source       = models.CharField(max_length=50, default="adaptive_v3.2")

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} – CA Assessment {self.timestamp.date()}"


class AdaptiveAssessment(models.Model):
    """Maps to mongo: db.adaptive_assessments"""
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name="adaptive_assessments")
    timestamp        = models.DateTimeField(auto_now_add=True)
    domain_scores    = models.JSONField(default=dict)
    overall_wellness = models.FloatField(default=0.0)
    ca_result        = models.JSONField(default=dict)
    ca_raw_mapped    = models.JSONField(default=dict)
    mh_compat        = models.JSONField(default=dict)
    answers_count    = models.IntegerField(default=0)
    algorithm        = models.CharField(max_length=100, default="adaptive_wellness_v3.2")

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} – Adaptive Assessment {self.timestamp.date()}"


class OutcomeCycle(models.Model):
    """Maps to mongo: db.outcome_cycles"""
    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name="outcome_cycles")
    protocol_id        = models.UUIDField(null=True, blank=True)
    cycle_start        = models.DateTimeField()
    cycle_end          = models.DateTimeField(auto_now_add=True)
    biomarker_deltas   = models.JSONField(default=dict)
    hps_delta          = models.JSONField(default=dict)
    protocol_summary   = models.JSONField(default=dict)
    adherence          = models.JSONField(default=dict)
    demographics       = models.JSONField(default=dict)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} – Outcome Cycle {self.created_at.date()}"


class HealthBrief(models.Model):
    """Maps to mongo: db.health_briefs"""
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name="health_briefs")
    trigger_type      = models.CharField(max_length=50) # consultation, lab_results, etc
    brief             = models.JSONField(default=dict)
    generated_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="generated_briefs")
    delivered         = models.BooleanField(default=False)
    delivery_channels = models.JSONField(default=list)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} – Health Brief {self.created_at.date()}"


# ──────────────────────────────────────────────
# 33. Privacy Settings
# ──────────────────────────────────────────────

class PrivacySetting(models.Model):
    """Maps to mongo: db.privacy_settings  (one record per user)"""
    user                    = models.OneToOneField(User, on_delete=models.CASCADE,
                                                   related_name="privacy_settings")
    share_hps               = models.BooleanField(default=True)
    share_biomarkers        = models.BooleanField(default=False)
    share_to_franchise      = models.BooleanField(default=True)
    share_to_care_team      = models.BooleanField(default=True)
    consent_data_processing = models.BooleanField(default=True)
    consent_ai_analysis     = models.BooleanField(default=True)
    allow_photo_posts       = models.BooleanField(default=True)
    blur_photos_non_team    = models.BooleanField(default=False)

    def __str__(self):
        return f"Privacy settings of {self.user.username}"


# ──────────────────────────────────────────────
# 34. Seasons  (franchise competition seasons)
# ──────────────────────────────────────────────

class Season(models.Model):
    """Maps to mongo: db.seasons"""
    STATUS_CHOICES = [
        ("upcoming", "Upcoming"),
        ("active",   "Active"),
        ("closed",   "Closed"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=255)
    description  = models.TextField(blank=True)
    start_date   = models.DateField()
    end_date     = models.DateField()
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="upcoming")
    created_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                      related_name="created_seasons")
    participants = models.ManyToManyField(User, related_name="seasons_joined", blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} ({self.status})"


# ──────────────────────────────────────────────
# 35. Medications / E-Prescriptions
# ──────────────────────────────────────────────

class Medication(models.Model):
    """Maps to mongo: db.medications  (active prescriptions for a member)"""
    STATUS_CHOICES = [
        ("active",     "Active"),
        ("discontinued", "Discontinued"),
        ("completed",  "Completed"),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member           = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medications")
    prescribed_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                          related_name="prescribed_medications")
    medication_name  = models.CharField(max_length=255)
    medication_type  = models.CharField(max_length=60, default="supplement")  # drug, supplement…
    dosage           = models.CharField(max_length=100, blank=True)
    frequency        = models.CharField(max_length=100, blank=True)
    route            = models.CharField(max_length=50, default="oral")
    duration_days    = models.IntegerField(default=90)
    refills_allowed  = models.IntegerField(default=0)
    clinical_notes   = models.TextField(blank=True)
    diagnosis_code   = models.CharField(max_length=20, blank=True)
    start_date       = models.DateField(null=True, blank=True)
    status           = models.CharField(max_length=30, choices=STATUS_CHOICES, default="active")
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.member.username} – {self.medication_name} ({self.status})"


# ──────────────────────────────────────────────
# 36. Lab Reports Repository
# ──────────────────────────────────────────────

class LabReport(models.Model):
    """Maps to mongo: db.lab_reports"""
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lab_reports")
    lab_partner      = models.CharField(max_length=100, blank=True)   # MedPlus, Thyrocare, …
    report_type      = models.CharField(max_length=60, default="blood_panel")
    ocr_text         = models.TextField(blank=True)
    extracted_values = models.JSONField(default=list)  # [{code, value, unit, status}, …]
    approved         = models.BooleanField(default=False)
    reviewed_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name="reviewed_lab_reports")
    report_date      = models.DateField(null=True, blank=True)
    uploaded_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.patient.username} – {self.report_type} {self.report_date or ''}"


# ──────────────────────────────────────────────
# 37. Outcome Learning Cycles  (AI feedback loops)
# ──────────────────────────────────────────────



class AITrainingRecord(models.Model):
    """Maps to mongo: db.ai_training_records  (anonymised data for model training)"""
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_cycle      = models.ForeignKey('OutcomeCycle', on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name="ai_training_records")
    anonymized_patient = models.JSONField(default=dict)  # age, gender, ethnicity (no PII)
    intervention      = models.JSONField(default=dict)   # protocol summary
    outcomes          = models.JSONField(default=dict)   # hps_delta, pillar_deltas, adherence
    consent_given     = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AITraining record {self.id}"


# ──────────────────────────────────────────────
# 38. Patient Chat Messages  (async secure messaging)
# ──────────────────────────────────────────────

class ChatMessage(models.Model):
    """Maps to mongo: db.chat_messages  (patient ↔ HCP secure messaging)"""
    MESSAGE_TYPE_CHOICES = [
        ("text",       "Text"),
        ("image",      "Image"),
        ("file",       "File"),
        ("voice",      "Voice Note"),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    recipient      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content        = models.TextField()
    message_type   = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default="text")
    attachment_url = models.URLField(blank=True, null=True)
    is_read        = models.BooleanField(default=False)
    sent_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_at"]
        indexes = [
            models.Index(fields=["sender", "recipient", "sent_at"]),
        ]

    def __str__(self):
        return f"{self.sender.username} → {self.recipient.username} ({self.sent_at.strftime('%Y-%m-%d %H:%M')})"


# ──────────────────────────────────────────────
# 39. User Address
# ──────────────────────────────────────────────

class UserAddress(models.Model):
    """Maps to mongo: users.address  (extracted as a proper table)"""
    ADDRESS_TYPE_CHOICES = [
        ("home",   "Home"),
        ("office", "Office"),
        ("other",  "Other"),
    ]

    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    address_type       = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default="home")
    address_line       = models.CharField(max_length=255, blank=True)
    landmark           = models.CharField(max_length=255, blank=True)
    city               = models.CharField(max_length=100, blank=True)
    state              = models.CharField(max_length=100, blank=True)
    pin_code           = models.CharField(max_length=10, blank=True)
    latitude           = models.FloatField(null=True, blank=True)
    longitude          = models.FloatField(null=True, blank=True)
    location_confirmed = models.BooleanField(default=False)
    is_default         = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.user.username} – {self.address_type}: {self.city}"


# ──────────────────────────────────────────────
# 40. Extended UserProfile fields from Flask
# (specialty, qualification, ethnicity, franchise, etc.)
# ──────────────────────────────────────────────

class HCPProfile(models.Model):
    """Health Care Professional profile — extends User for clinician/coach roles."""
    ROLE_CHOICES = [
        ("longevity_physician",     "Longevity Physician"),
        ("fitness_coach",           "Fitness Coach"),
        ("psychologist",            "Psychologist"),
        ("physical_therapist",      "Physical Therapist"),
        ("nutritional_coach",       "Nutritional Coach"),
        ("nurse_navigator",         "Nurse Navigator"),
        ("corporate_hr_admin",      "Corporate HR Admin"),
        ("corporate_wellness_head", "Corporate Wellness Head"),
        ("cxo_executive",           "CXO Executive"),
        ("support_agent",           "Support Agent"),
        ("clinician",               "Clinician"),
        ("coach",                   "Coach"),
        ("medical_director",        "Medical Director"),
        ("clinical_admin",          "Clinical Admin"),
        ("phlebotomist",            "Phlebotomist"),
    ]

    user            = models.OneToOneField(User, on_delete=models.CASCADE,
                                           related_name="hcp_profile")
    role            = models.CharField(max_length=60, choices=ROLE_CHOICES)
    specialty       = models.CharField(max_length=255, blank=True)
    qualification   = models.CharField(max_length=255, blank=True)
    bio             = models.TextField(blank=True)
    availability    = models.JSONField(default=dict, blank=True)
    notification_prefs = models.JSONField(default=dict, blank=True)
    age             = models.PositiveIntegerField(null=True, blank=True)
    sex             = models.CharField(max_length=10, blank=True)  # M / F / Other
    height_cm       = models.FloatField(default=170)
    weight_kg       = models.FloatField(default=70)
    ethnicity       = models.CharField(max_length=60, default="SOUTH_ASIAN")
    franchise       = models.CharField(max_length=120, blank=True)
    managed_conditions = models.JSONField(default=list)
    adherence_pct   = models.FloatField(default=0.0)
    streak_days     = models.IntegerField(default=0)
    is_demo         = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} – {self.role}"


# ──────────────────────────────────────────────
# 41. Health Snapshots  (photo/media uploads)
# ──────────────────────────────────────────────

class HealthSnapshot(models.Model):
    """Maps to mongo: db.health_snapshots"""
    CATEGORY_CHOICES = [
        ("meal",        "Meal"),
        ("workout",     "Workout"),
        ("sleep",       "Sleep"),
        ("progress",    "Progress"),
        ("lab_result",  "Lab Result"),
        ("supplements", "Supplements"),
        ("other",       "Other"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="health_snapshots")
    category     = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="other")
    notes        = models.TextField(blank=True)
    filename     = models.CharField(max_length=255)
    content_type = models.CharField(max_length=80, default="image/jpeg")
    size_bytes   = models.IntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} – {self.category} ({self.created_at.date()})"


# ──────────────────────────────────────────────
# 42. Daily Dopamine Challenges  (per-user, per-day)
# ──────────────────────────────────────────────

class DailyChallenge(models.Model):
    """Maps to mongo: db.daily_challenges"""
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_challenges")
    date           = models.CharField(max_length=10)          # "YYYY-MM-DD"
    title          = models.CharField(max_length=255)
    description    = models.TextField(blank=True)
    challenge_type = models.CharField(max_length=60, default="wellness")
    xp             = models.IntegerField(default=0)
    surprise_reward = models.CharField(max_length=255, blank=True)
    completed      = models.BooleanField(default=False)
    completed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.username} – {self.date} ({self.title})"


# ──────────────────────────────────────────────
# 43. Badge Catalog  (was BADGE_CATALOG constant)
# ──────────────────────────────────────────────

class BadgeCatalog(models.Model):
    """
    Stores all available badge definitions.
    Replaces the hardcoded BADGE_CATALOG list in hps_engine/employee.py.
    Seeded via: python manage.py seed_static_data
    """
    TIER_CHOICES = [
        ("bronze", "Bronze"),
        ("silver", "Silver"),
        ("gold",   "Gold"),
    ]
    CATEGORY_CHOICES = [
        ("milestone",   "Milestone"),
        ("tier",        "Tier"),
        ("streak",      "Streak"),
        ("improvement", "Improvement"),
        ("integration", "Integration"),
        ("challenge",   "Challenge"),
        ("social",      "Social"),
        ("competition", "Competition"),
        ("nutrition",   "Nutrition"),
        ("health",      "Health"),
    ]

    code        = models.CharField(max_length=60, unique=True)
    name        = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    icon        = models.CharField(max_length=60, default="award")
    category    = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="milestone")
    tier        = models.CharField(max_length=10, choices=TIER_CHOICES, default="bronze")
    requirement = models.CharField(max_length=255, blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering = ["tier", "name"]

    def __str__(self):
        return f"[{self.tier.upper()}] {self.name} ({self.code})"

    def to_dict(self):
        """Return dict identical to the old BADGE_CATALOG list entry."""
        return {
            "code":        self.code,
            "name":        self.name,
            "description": self.description,
            "icon":        self.icon,
            "category":    self.category,
            "tier":        self.tier,
            "requirement": self.requirement,
        }


# ──────────────────────────────────────────────
# 44. Dopamine Challenge Template  (was DAILY_DOPAMINE_CHALLENGES constant)
# ──────────────────────────────────────────────

class DopamineChallengeTemplate(models.Model):
    """
    Pool of daily dopamine challenge templates.
    Replaces the hardcoded DAILY_DOPAMINE_CHALLENGES list in views_employee.py.
    One template is picked per user per day (deterministically by seed).
    Seeded via: python manage.py seed_static_data
    """
    title        = models.CharField(max_length=200)
    description  = models.TextField()
    challenge_type = models.CharField(max_length=60, default="wellness")
    xp           = models.IntegerField(default=15)
    surprise_pool = models.JSONField(default=list)   # list of strings e.g. ["5 bonus credits", ...]
    is_active    = models.BooleanField(default=True)
    sort_order   = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.title} ({self.challenge_type}, {self.xp} XP)"

    def to_dict(self):
        """Return dict identical to the old DAILY_DOPAMINE_CHALLENGES list entry."""
        return {
            "title":         self.title,
            "description":   self.description,
            "type":          self.challenge_type,
            "xp":            self.xp,
            "surprise_pool": self.surprise_pool,
        }

# ──────────────────────────────────────────────
# 45. Health API Integration Models
# ──────────────────────────────────────────────

class OrganSystem(models.Model):
    """Stores configuration for organ age calculation and suggestions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default="activity")
    biomarkers = models.JSONField(default=list) # ["hrv_rmssd", ...]
    proxy_biomarkers = models.JSONField(default=list)
    pillar_weights = models.JSONField(default=dict) # {"BR": 0.6, ...}
    conditions_risk = models.JSONField(default=list) # ["hypertension", ...]
    behavioral_keys = models.JSONField(default=list) # ["smoking_score", ...]
    suggested_tests = models.JSONField(default=list) # [{"test": "ECG", ...}, ...]
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class AppointmentService(models.Model):
    """Available health services for booking."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    service_type = models.CharField(max_length=50) # medical, coaching, etc.
    duration = models.IntegerField(default=30)
    modes = models.JSONField(default=list) # ["physical", "virtual"]
    
    def __str__(self):
        return self.name

class MedicalCondition(models.Model):
    """Maps to mongo: db.medical_conditions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medical_conditions")
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default="stable") # stable, improving, attention
    diagnosed_date = models.DateField(null=True, blank=True)
    icd10 = models.CharField(max_length=20, blank=True)
    severity = models.CharField(max_length=20, default="mild")
    care_plan = models.JSONField(default=dict)
    relevant_biomarkers = models.JSONField(default=list)
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"

class MedicationLog(models.Model):
    """Tracks medication compliance."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medication_logs")
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name="logs")
    medication_name = models.CharField(max_length=255)
    date = models.DateField(default=timezone.now)
    logged_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        get_latest_by = "logged_at"

class RefillRequest(models.Model):
    """Requests for medication refills."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refill_requests")
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name="refill_requests")
    medication_name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default="requested") # requested, approved, completed
    requested_at = models.DateTimeField(auto_now_add=True)
    care_team_notified = models.BooleanField(default=True)

class SOSAlert(models.Model):
    """Emergency SOS alerts from employees."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sos_alerts")
    user_name = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=20, default="high")
    status = models.CharField(max_length=20, default="active") # active, resolved
    triggered_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    care_team_notified = models.BooleanField(default=True)
    franchise = models.CharField(max_length=100, default="Independent")

    def __str__(self):
        return f"SOS: {self.user_name} ({self.triggered_at})"


# ──────────────────────────────────────────────
# 46. Additional EMR Models Parity
# ──────────────────────────────────────────────

class EMRAllergy(models.Model):
    """Maps to mongo: db.emr_allergies"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emr_allergies")
    allergen = models.CharField(max_length=255)
    category = models.CharField(max_length=100, default="drug") # drug, food, environmental
    reaction = models.CharField(max_length=255, blank=True)
    severity = models.CharField(max_length=50, default="mild") # mild, moderate, severe
    status = models.CharField(max_length=50, default="active") # active, inactive
    identified_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.username} - Allergy: {self.allergen}"


class DiagnosticCatalog(models.Model):
    """Catalog of available diagnostic tests (Radiology, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=100)
    loinc = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class DiagnosticOrder(models.Model):
    """Maps to mongo: db.diagnostics_orders"""
    URGENCY_CHOICES = [
        ("routine", "Routine"),
        ("urgent",  "Urgent"),
        ("stat",    "STAT / Emergency"),
    ]
    STATUS_CHOICES = [
        ("ordered",   "Ordered"),
        ("collected", "Collected"),
        ("processed", "Processed"),
        ("resulted",  "Resulted"),
        ("reviewed",  "Reviewed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="diagnostic_orders")
    ordered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_diagnostic_orders")
    test_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100) # Radiology, Cardiac, etc.
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default="routine")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ordered")
    reason = models.TextField(blank=True)
    results_summary = models.TextField(blank=True)
    abnormal_flag = models.BooleanField(default=False)
    ordered_at = models.DateTimeField(auto_now_add=True)
    resulted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.member.username} - {self.test_name} ({self.status})"

# ──────────────────────────────────────────────
# 45. Clinical Care Coordination (CC)
# ──────────────────────────────────────────────

class CCAlert(models.Model):
    """Maps to mongo: db.cc_alerts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cc_alerts")
    member_name = models.CharField(max_length=255, blank=True)
    biomarker = models.CharField(max_length=100, blank=True)
    severity = models.CharField(max_length=20, choices=[("CRITICAL", "Critical"), ("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")], default="MEDIUM")
    aps_score = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="open")  # open / resolved / acknowledged
    ai_interpretation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cc = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_alerts")

    class Meta:
        ordering = ["-aps_score", "-created_at"]

    def __str__(self):
        return f"[{self.severity}] {self.biomarker} Alert for {self.member.username}"

class NFLETask(models.Model):
    """Maps to mongo: db.nfle_tasks  (Next-Flow Logic Engine Tasks)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="nfle_tasks")
    member_name = models.CharField(max_length=255, blank=True)
    rule_biomarker = models.CharField(max_length=100, blank=True)
    biomarker_value = models.FloatField(null=True, blank=True)
    threshold = models.FloatField(null=True, blank=True)
    condition = models.CharField(max_length=10, blank=True) # ">" or "<"
    task_description = models.TextField(blank=True)
    assigned_roles = models.JSONField(default=list) # List of roles like ["longevity_physician"]
    priority = models.CharField(max_length=20, default="medium")
    protocol_suggestion = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task_description} for {self.member.username}"

class Escalation(models.Model):
    """Maps to mongo: db.escalations  (Coach to Clinician escalations)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clinical_escalations")
    member_name = models.CharField(max_length=255, blank=True)
    coach = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sent_escalations")
    coach_name = models.CharField(max_length=255, blank=True)
    severity = models.CharField(max_length=20, default="medium")
    category = models.CharField(max_length=100, default="review")
    clinical_summary = models.TextField(blank=True)
    handoff_note = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default="pending") # pending / reviewed / resolved
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Escalation for {self.member.username} by {self.coach_name}"

class CCReferral(models.Model):
    """Maps to mongo: db.cc_referrals (specific referral tracking for AI and CC)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cc_referrals")
    member_name = models.CharField(max_length=255, blank=True)
    referral_type = models.CharField(max_length=100, blank=True)
    reason = models.TextField(blank=True)
    referred_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_cc_referrals")
    referred_to_name = models.CharField(max_length=255, blank=True)
    priority = models.CharField(max_length=20, default="normal")
    status = models.CharField(max_length=20, default="pending")
    notes = models.TextField(blank=True)
    referring_clinician_id = models.CharField(max_length=100, blank=True)
    referring_clinician_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"CCReferral: {self.member_name} to {self.referred_to_name}"



class CCAssignment(models.Model):
    """Maps to mongo: db.cc_assignments"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cc = models.ForeignKey(User, on_delete=models.CASCADE, related_name="managed_members")
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assigned_coordinators")
    role = models.CharField(max_length=50, default="primary_clinician") # primary_clinician, primary_coach, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["cc", "member", "role"]

    def __str__(self):
        return f"{self.cc.username} -> {self.member.username} ({self.role})"

class CCSession(models.Model):
    """Maps to mongo: db.cc_sessions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cc = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cc_sessions")
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="member_cc_sessions")
    session_type = models.CharField(max_length=50, default="check-in")
    scheduled_at = models.DateTimeField()
    duration_min = models.IntegerField(default=30)
    status = models.CharField(max_length=20, default="scheduled") # scheduled / completed / cancelled
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"{self.session_type} for {self.member.username} on {self.scheduled_at}"


# ──────────────────────────────────────────────
# 15. Miscellaneous — Care Team
# ──────────────────────────────────────────────

class CareTeamMember(models.Model):
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user                = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="care_member")
    name                = models.CharField(max_length=150)
    role                = models.CharField(max_length=100)
    specialization      = models.CharField(max_length=200)
    email               = models.EmailField()
    status              = models.CharField(max_length=20, default="active")
    credits_per_session = models.IntegerField(default=15)

    def __str__(self):
        return f"{self.name} ({self.role})"


class CareTeamReview(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE)
    member       = models.ForeignKey(CareTeamMember, on_delete=models.CASCADE, related_name="reviews")
    rating       = models.IntegerField()
    nps_score    = models.IntegerField(null=True, blank=True)
    review_text  = models.TextField(blank=True)
    created_at   = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Review for {self.member.name} by {self.user.username}"
