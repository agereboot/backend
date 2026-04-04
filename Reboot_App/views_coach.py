import uuid
from datetime import datetime, timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth.models import User

from .models import (
    CoachTask, FitnessProfile, ExerciseProgramme, ExerciseSessionLog,
    CBTModule, CBTAssignment, TherapyNote, CrisisAlert, BehaviorLog,
    NutritionalProfile, MealPlan, SupplementStack, UserProfile,
    HPSScore, BiomarkerResult, CCAssignment, Appointment, CCMessage,
    TherapyProgram, MealPlanDay, NutritionConsultationNote, HCPProfile, Escalation
)
from .serializers_coach import (
    CoachTaskSerializer, FitnessProfileSerializer, ExerciseProgrammeSerializer,
    ExerciseSessionLogSerializer, CBTModuleSerializer, CBTAssignmentSerializer,
    TherapyNoteSerializer, CrisisAlertSerializer, NutritionalProfileSerializer,
    MealPlanSerializer, SupplementStackSerializer, TherapyProgramSerializer,
    MealPlanDaySerializer, NutritionConsultationNoteSerializer, HCPProfileSerializer,
    EscalationSerializer
)
from .serializers import CCMessageSerializer
from .serializers import CCAssignmentSerializer

# Helpers
def _require_coach(user):
    try:
        role_name = user.profile.role.name
    except AttributeError:
        return False
    COACH_ROLES = {"fitness_coach", "psychologist", "nutritional_coach", "coach", "clinician", "longevity_physician", "medical_director"}
    return role_name in COACH_ROLES

def coach_auth_check(view_func):
    def wrapper(request, *args, **kwargs):
        if not _require_coach(request.user):
            return Response({"error": "HCP role required"}, status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

# ═══════════════════════════════════════════════════════════════════
# EXISTING COACH API (RESTORED)
# ═══════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_coach_assignments(request):
    assignments = CCAssignment.objects.filter(cc=request.user)
    serializer = CCAssignmentSerializer(assignments, many=True)
    return Response({"assignments": serializer.data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def create_coach_assignment(request):
    member_id = request.data.get("member_id")
    role = request.data.get("role", "coach")
    member = get_object_or_404(User, id=member_id)
    
    assignment, created = CCAssignment.objects.get_or_create(
        member=member,
        cc=request.user,
        defaults={"role": role}
    )
    return Response(CCAssignmentSerializer(assignment).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_member_vitals(request, member_id):
    member = get_object_or_404(User, id=member_id)
    # Get latest vitals from biomarkers
    vitals_codes = ["hr", "bp_sys", "bp_dia", "spo2", "temperature", "respiratory_rate"]
    results = BiomarkerResult.objects.filter(user=member, biomarker_id__in=vitals_codes).order_by('biomarker_id', '-collected_at').distinct('biomarker_id')
    
    data = {r.biomarker_id: r.value for r in results}
    return Response({"vitals": data, "member_id": member_id})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_member_details(request, member_id):
    member = get_object_or_404(User, id=member_id)
    profile = member.profile
    hps = HPSScore.objects.filter(user=member).first()
    
    return Response({
        "member": {
            "id": member.id,
            "username": member.username,
            "name": member.get_full_name(),
            "age": profile.age,
            "gender": profile.gender,
            "hps_score": hps.hps_final if hps else None,
            "tier": hps.tier if hps else "UNKNOWN"
        }
    })

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def manage_coach_feedback(request):
    # Simplified feedback logic
    if request.method == 'GET':
        return Response({"feedback": []})
    return Response({"status": "feedback_received"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def log_coach_session(request):
    """Legacy endpoint mapping to log_pfc_session logic."""
    return log_pfc_session(request._request)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def generate_workout_plan(request):
    """Stub for AI workout generation."""
    return Response({
        "status": "success",
        "plan_id": str(uuid.uuid4()),
        "exercises": ["Warm up", "Main set", "Cool down"]
    })

# ═══════════════════════════════════════════════════════════════════
# SHARED: Task Queue
# ═══════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_task_queue(request):
    status_filter = request.query_params.get('status', '')
    tasks = CoachTask.objects.filter(assigned_to=request.user)
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    serializer = CoachTaskSerializer(tasks.order_by('-created_at'), many=True)
    return Response({"tasks": serializer.data})

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def complete_task(request, task_id):
    task = get_object_or_404(CoachTask, id=task_id, assigned_to=request.user)
    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    task.completion_notes = request.data.get("notes", "")
    task.save()
    return Response({"status": "completed"})

# ═══════════════════════════════════════════════════════════════════
# PFC: Physical Fitness Coach Module
# ═══════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_fitness_profile(request, member_id):
    member = get_object_or_404(User, id=member_id)
    profile, created = FitnessProfile.objects.get_or_create(member=member)
    
    # Enrich with latest vitals and HPS if missing in legacy-style response
    data = FitnessProfileSerializer(profile).data
    
    # Get latest HPS
    hps = HPSScore.objects.filter(user=member).first()
    if hps:
        data["hps_pf_score"] = hps.pillars.get("PF", {}).get("percentage", hps.pillars.get("physical_fitness", 0))
        data["hps_total"] = hps.hps_final
    
    # Mock/Legacy adherence for now
    data["adherence_rate_30d"] = 0
    
    return Response({"profile": data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def save_fitness_profile(request, member_id):
    member = get_object_or_404(User, id=member_id)
    profile, _ = FitnessProfile.objects.get_or_create(member=member)
    
    # Update fields from data
    if "training_experience" in request.data:
        profile.training_experience = request.data["training_experience"]
    if "exercise_preferences" in request.data:
        profile.exercise_preferences = request.data["exercise_preferences"]
    if "equipment_access" in request.data:
        profile.equipment_access = request.data["equipment_access"]
    if "injury_log" in request.data:
        profile.injury_log = request.data["injury_log"]
        
    profile.updated_by = request.user
    profile.save()
    return Response({"status": "saved"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_programmes(request):
    member_id = request.query_params.get('member_id')
    progs = ExerciseProgramme.objects.filter(coach=request.user)
    if member_id:
        progs = progs.filter(member_id=member_id)
    
    serializer = ExerciseProgrammeSerializer(progs.order_by('-created_at'), many=True)
    return Response({"programmes": serializer.data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def create_programme(request):
    data = request.data
    member_id = data.get("member_id")
    member = get_object_or_404(User, id=member_id)
    
    prog = ExerciseProgramme.objects.create(
        coach=request.user,
        member=member,
        name=data.get("name", "Untitled Programme"),
        primary_goal=data.get("primary_goal", "longevity"),
        duration_weeks=data.get("duration_weeks", 12),
        training_days_per_week=data.get("training_days_per_week", 4),
        session_duration_min=data.get("session_duration_min", 45),
        exercises=data.get("exercises", []),
        clinician_protocol=data.get("clinician_protocol")
    )
    
    return Response(ExerciseProgrammeSerializer(prog).data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def approve_programme(request, prog_id):
    prog = get_object_or_404(ExerciseProgramme, id=prog_id)
    prog.status = "active"
    prog.approved_at = datetime.now(timezone.utc)
    prog.save()
    return Response({"status": "active"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def log_pfc_session(request):
    data = request.data
    member_id = data.get("member_id")
    member = get_object_or_404(User, id=member_id)
    prog_id = data.get("programme_id")
    prog = ExerciseProgramme.objects.filter(id=prog_id).first() if prog_id else None
    
    log = ExerciseSessionLog.objects.create(
        coach=request.user,
        member=member,
        programme=prog,
        exercises_completed=data.get("exercises_completed", []),
        session_rpe=data.get("session_rpe"),
        compliance_pct=data.get("compliance_pct", 100),
        notes=data.get("notes", "")
    )
    
    return Response(ExerciseSessionLogSerializer(log).data)

# ═══════════════════════════════════════════════════════════════════
# PSY: Psychology Therapist Module
# ═══════════════════════════════════════════════════════════════════

ASSESSMENT_TEMPLATES = {
    "PHQ-9": {"name": "Patient Health Questionnaire-9", "questions": 9, "max_score": 27},
    "GAD-7": {"name": "Generalized Anxiety Disorder-7", "questions": 7, "max_score": 21},
    "PSQI": {"name": "Pittsburgh Sleep Quality Index", "questions": 19, "max_score": 21},
}

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_assessment_templates(request):
    return Response({"templates": ASSESSMENT_TEMPLATES})

# PHQ-9/GAD-7 Results logic in Reboot is handled by CognitiveAssessmentResult
# but the legacy API uses a specific PSY assessments collection. 
# We'll map to CBT/TherapyNote and general sessions for now.

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_psy_cbt_modules(request):
    modules = CBTModule.objects.all()
    if not modules.exists():
        # Seed basic modules if empty
        CBTModule.objects.create(name="Cognitive Restructuring", category="CBT Core", sessions=8, description="Identify negative thought patterns.")
        CBTModule.objects.create(name="Sleep Restriction Therapy", category="Sleep", sessions=6, description="Treat chronic insomnia.")
        modules = CBTModule.objects.all()
    
    return Response({"modules": CBTModuleSerializer(modules, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def assign_cbt_module(request):
    data = request.data
    member = get_object_or_404(User, id=data.get("member_id"))
    module = get_object_or_404(CBTModule, id=data.get("module_id"))
    
    assignment = CBTAssignment.objects.create(
        module=module,
        member=member,
        assigned_by=request.user,
        total_sessions=data.get("total_sessions", 8)
    )
    return Response(CBTAssignmentSerializer(assignment).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_crisis_alerts(request):
    alerts = CrisisAlert.objects.filter(status="active")
    return Response({"alerts": CrisisAlertSerializer(alerts, many=True).data})

# ═══════════════════════════════════════════════════════════════════
# NUT: Nutritional Coach Module
# ═══════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_nutritional_profile(request, member_id):
    member = get_object_or_404(User, id=member_id)
    profile, _ = NutritionalProfile.objects.get_or_create(member=member)
    return Response({"profile": NutritionalProfileSerializer(profile).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def save_nutritional_profile(request, member_id):
    member = get_object_or_404(User, id=member_id)
    profile, _ = NutritionalProfile.objects.get_or_create(member=member)
    
    for attr, value in request.data.items():
        if hasattr(profile, attr):
            setattr(profile, attr, value)
    
    # Auto-calculate macros if data exists
    if profile.weight_kg and profile.height_cm:
        # Simplified formula
        target = profile.target_kcal or 2000
        profile.macros = {
            "protein_g": round(profile.weight_kg * 1.8),
            "fat_g": round(target * 0.3 / 9),
            "carb_g": round(target * 0.4 / 4)
        }
        
    profile.save()
    return Response({"status": "saved", "profile": NutritionalProfileSerializer(profile).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def create_meal_plan(request):
    data = request.data
    member = get_object_or_404(User, id=data.get("member_id"))
    
    plan = MealPlan.objects.create(
        coach=request.user,
        member=member,
        name=data.get("name", "7-Day Meal Plan"),
        target_kcal=data.get("target_kcal"),
        macros=data.get("macros", {}),
        meals=data.get("meals", []),
        supplements=data.get("supplements", [])
    )
    return Response(MealPlanSerializer(plan).data)

# ═══════════════════════════════════════════════════════════════════
# SHARED: Dashboard Stats
# ═══════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_coach_dashboard(request):
    role = request.user.profile.role.name
    
    # Get assigned members
    member_ids = CCAssignment.objects.filter(cc=request.user).values_list('member_id', flat=True)
    # Also include those with appointments
    appt_member_ids = Appointment.objects.filter(assigned_hcp=request.user).values_list('member_id', flat=True)
    all_member_ids = list(set(list(member_ids) + list(appt_member_ids)))
    
    base = {
        "total_members": len(all_member_ids),
        "pending_tasks": CoachTask.objects.filter(assigned_to=request.user, status="pending").count(),
        "today_appointments": [], # Query appointments table if needed
        "role_type": "GENERIC"
    }
    
    if "fitness" in role: 
        base["role_type"] = "PFC"
        base["active_programmes"] = ExerciseProgramme.objects.filter(coach=request.user, status="active").count()
    elif "psych" in role:
        base["role_type"] = "PSY"
        base["crisis_alerts"] = CrisisAlert.objects.filter(status="active").count()
    elif "nutrit" in role:
        base["role_type"] = "NUT"
        base["active_meal_plans"] = MealPlan.objects.filter(coach=request.user, status="active").count()

    # Spotlight
    spotlight = []
    for mid in all_member_ids[:5]:
        m = User.objects.get(id=mid)
        hps = HPSScore.objects.filter(user=m).first()
        spotlight.append({
            "id": mid,
            "name": m.get_full_name() or m.username,
            "hps_total": hps.hps_final if hps else None
        })
    base["member_spotlight"] = spotlight
    
    return Response(base)

# ═══════════════════════════════════════════════════════════════════
# ADDITIONAL COACH API (MIGRATED FROM FASTAPI)
# ═══════════════════════════════════════════════════════════════════

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def manage_coach_messages(request):
    if request.method == 'GET':
        member_id = request.query_params.get('member_id')
        messages = CCMessage.objects.filter(Q(sender=request.user) | Q(recipient=request.user))
        if member_id:
            messages = messages.filter(Q(sender_id=member_id) | Q(recipient_id=member_id))
        return Response({"messages": CCMessageSerializer(messages.order_by('sent_at'), many=True).data})
    
    data = request.data
    msg = CCMessage.objects.create(
        sender=request.user,
        recipient_id=data.get("recipient_id"),
        content=data.get("content"),
        message_type=data.get("message_type", "text")
    )
    return Response(CCMessageSerializer(msg).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_pfc_wearable_feed(request):
    """Simulated wearable feed for assigned members."""
    member_ids = CCAssignment.objects.filter(cc=request.user).values_list('member_id', flat=True)
    feed = []
    # Mock some data for now
    for mid in member_ids[:10]:
        feed.append({
            "member_id": mid,
            "steps": 8500,
            "hr_avg": 72,
            "sleep_hrs": 7.5,
            "last_sync": datetime.now(timezone.utc).isoformat()
        })
    return Response({"feed": feed})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def manage_psy_assessments(request, member_id=None):
    if request.method == 'GET':
        # Legacy PSY assessments often used HPS results as sources
        # but here we'll return structured assessment logs if they exist.
        return Response({"assessments": []})
    
    # POST - Administer new assessment (Mock)
    return Response({"status": "assessment_administered", "id": str(uuid.uuid4())})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def interpret_assessment(request, assessment_id):
    """AI interpretation stub."""
    return Response({
        "interpretation": "Analysis of clinical data indicates moderate stress with high work-life imbalance. Recommendations include prioritizing sleep hygiene and implementing 5-minute mindfulness breaks.",
        "ai_model": "claude-3-haiku-stub"
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def resolve_crisis_alert(request, alert_id):
    alert = get_object_or_404(CrisisAlert, id=alert_id)
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolution_notes = request.data.get("notes", "")
    alert.save()
    return Response({"status": "resolved"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def list_nut_meal_plans(request):
    member_id = request.query_params.get('member_id')
    plans = MealPlan.objects.all()
    if member_id:
        plans = plans.filter(member_id=member_id)
    return Response({"plans": MealPlanSerializer(plans, many=True).data})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def manage_nut_supplements(request):
    if request.method == 'GET':
        # Library/Catalog
        return Response({"supplements": [
            {"id": "s1", "name": "Vitamin D3", "dosage": "2000 IU"},
            {"id": "s2", "name": "Omega-3", "dosage": "1000mg"}
        ]})
    
    # Assign
    data = request.data
    stack = SupplementStack.objects.create(
        member_id=data.get("member_id"),
        coach=request.user,
        supplements=data.get("supplements", [])
    )
    return Response(SupplementStackSerializer(stack).data)
