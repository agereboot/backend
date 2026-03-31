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
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
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
    reward = models.CharField(max_length=255)
    rules = models.TextField()

    start_date = models.DateField()
    end_date = models.DateField()

    challenge_type = models.CharField(max_length=100)  # ex: AgeReboot-TN

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

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    progress = models.PositiveIntegerField(default=0)  # %
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="joined")

    joined_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("challenge", "user")

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


class CCProtocol(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lgp_id = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    evidence_grade = models.CharField(max_length=50)
    intervention_type = models.CharField(max_length=100)
    duration_weeks = models.IntegerField(default=12)
    expected_outcomes = models.JSONField(default=list)
    hps_dimensions = models.JSONField(default=list)
    impact_scores = models.JSONField(default=dict)
    contraindications = models.JSONField(default=list)
    drug_interactions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)


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

class BiomarkerResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="biomarkers")
    biomarker_name = models.CharField(max_length=100)
    value = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=20, null=True, blank=True)
    ingested_at = models.DateTimeField(default=timezone.now)
    observed_at = models.DateTimeField(null=True, blank=True)

class WearableConnection(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wearable")
    connected = models.BooleanField(default=False)
    device_type = models.CharField(max_length=100, null=True, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)

class LabOrder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lab_orders")
    tests = models.JSONField(default=list)
    status = models.CharField(max_length=50, default="ordered")
    ordered_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

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
    status = models.CharField(max_length=50, default="open")
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
    status = models.CharField(max_length=50, default="open")
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