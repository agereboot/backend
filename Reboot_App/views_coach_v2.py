import uuid
from datetime import datetime, timezone, timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Sum
from django.contrib.auth.models import User

from .models import (
    Habit, HabitLog, Challenge, ChallengeParticipant, CheckIn,
    Goal, ResourceShare, BodyComposition, TherapyNote, NutritionalProfile,
    CCSession, TherapyProgram, MealPlanDay, NutritionConsultationNote, HCPProfile, Escalation,
    HPSScore, BiomarkerResult, CCAssignment, CrisisAlert, BehaviorLog, MealPlan
)
from .serializers_coach import (
    HabitSerializer, HabitLogSerializer, CheckInSerializer,
    GoalSerializer, ResourceShareSerializer, BodyCompositionSerializer,
    TherapyNoteSerializer, TherapyProgramSerializer, MealPlanDaySerializer,
    NutritionConsultationNoteSerializer, HCPProfileSerializer, EscalationSerializer,
    BehaviorLogSerializer, MealPlanSerializer
)

# Helpers
def _require_coach(user):
    try:
        role_name = user.profile.role.name
    except AttributeError:
        return False
    COACH_ROLES = {"fitness_coach", "psychologist", "nutritional_coach", "coach", "longevity_physician", "clinician", "medical_director", "corporate_hr_admin"}
    return role_name in COACH_ROLES

def coach_auth_check(view_func):
    def wrapper(request, *args, **kwargs):
        if not _require_coach(request.user):
            return Response({"error": "Coach role required"}, status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

# ═══════════════════════════════════════════════════════════════
# HABIT TRACKING (PFC)
# ═══════════════════════════════════════════════════════════════

HABIT_TEMPLATES = [
    {"id": "h1", "name": "Morning Exercise", "category": "exercise", "icon": "dumbbell", "default_frequency": "daily"},
    {"id": "h2", "name": "10,000 Steps", "category": "activity", "icon": "footprints", "default_frequency": "daily"},
    {"id": "h3", "name": "Meditation", "category": "mindfulness", "icon": "brain", "default_frequency": "daily"},
    {"id": "h4", "name": "Hydration (8 glasses)", "category": "hydration", "icon": "droplets", "default_frequency": "daily"},
]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_habit_templates(request):
    return Response({"templates": HABIT_TEMPLATES})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def assign_habit(request):
    data = request.data
    member = get_object_or_404(User, id=data.get("member_id"))
    
    habit = Habit.objects.create(
        member=member,
        name=data.get("habit_name"),
        category=data.get("category", "general"),
        frequency=data.get("frequency", "daily"),
        assigned_by=request.user
    )
    return Response(HabitSerializer(habit).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_member_habits(request, member_id):
    member = get_object_or_404(User, id=member_id)
    habits = Habit.objects.filter(member=member, status="active")
    logs = HabitLog.objects.filter(member=member).order_by("-date")[:50]
    
    # Enrich habits with simplified streak/completion data
    habits_data = HabitSerializer(habits, many=True).data
    for h in habits_data:
        h_logs = HabitLog.objects.filter(habit_id=h["id"]).order_by("-date")
        h["completion_rate"] = 0
        if h_logs.exists():
            completed = h_logs.filter(completed=True).count()
            h["completion_rate"] = round(completed / h_logs.count() * 100)
            # Basic streak calculation
            streak = 0
            for l in h_logs:
                if l.completed: streak += 1
                else: break
            h["streak"] = streak
            
    return Response({"habits": habits_data, "logs": HabitLogSerializer(logs, many=True).data})

# ═══════════════════════════════════════════════════════════════
# CHECK-IN SYSTEM
# ═══════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_check_ins(request, member_id):
    check_ins = CheckIn.objects.filter(member_id=member_id).order_by("-created_at")
    return Response({"check_ins": CheckInSerializer(check_ins, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def create_check_in(request):
    data = request.data
    member = get_object_or_404(User, id=data.get("member_id"))
    
    ci = CheckIn.objects.create(
        member=member,
        mood_rating=data.get("mood_rating", 5),
        energy_level=data.get("energy_level", 5),
        sleep_quality=data.get("sleep_quality", 5),
        stress_level=data.get("stress_level", 5),
        adherence_self_rating=data.get("adherence_self_rating", 7),
        coach_notes=data.get("coach_notes", ""),
        conducted_by=request.user
    )
    return Response(CheckInSerializer(ci).data)

# ═══════════════════════════════════════════════════════════════
# GOALS TRACKER
# ═══════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_member_goals(request, member_id):
    goals = Goal.objects.filter(member_id=member_id).order_by("-created_at")
    return Response({"goals": GoalSerializer(goals, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def create_goal(request):
    data = request.data
    member = get_object_or_404(User, id=data.get("member_id"))
    
    goal = Goal.objects.create(
        member=member,
        category=data.get("category", "general"),
        title=data.get("title"),
        target_value=data.get("target_value"),
        deadline=data.get("deadline"),
        created_by=request.user
    )
    return Response(GoalSerializer(goal).data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def update_goal_progress(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id)
    goal.current_value = request.data.get("current_value", goal.current_value)
    if goal.target_value and goal.current_value >= goal.target_value:
        goal.status = "completed"
    goal.save()
    return Response(GoalSerializer(goal).data)

# ═══════════════════════════════════════════════════════════════
# PSY: Therapy Session Notes
# ═══════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_therapy_notes(request, member_id):
    notes = TherapyNote.objects.filter(member_id=member_id).order_by("-session_date")
    return Response({"notes": TherapyNoteSerializer(notes, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def create_therapy_note(request):
    data = request.data
    member = get_object_or_404(User, id=data.get("member_id"))
    
    note = TherapyNote.objects.create(
        member=member,
        therapist=request.user,
        subjective=data.get("subjective", ""),
        objective=data.get("objective", ""),
        assessment=data.get("assessment", ""),
        plan=data.get("plan", ""),
        risk_assessment=data.get("risk_assessment", "none"),
        interventions_used=data.get("interventions_used", [])
    )
    return Response(TherapyNoteSerializer(note).data)

# ═══════════════════════════════════════════════════════════════
# NUT: Body Composition
# ═══════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_body_comp(request, member_id):
    entries = BodyComposition.objects.filter(member_id=member_id).order_by("-date")
    return Response({"entries": BodyCompositionSerializer(entries, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def log_body_comp(request):
    data = request.data
    member = get_object_or_404(User, id=data.get("member_id"))
    
    entry = BodyComposition.objects.create(
        member=member,
        date=data.get("date", datetime.now(timezone.utc).date()),
        weight_kg=data.get("weight_kg"),
        body_fat_pct=data.get("body_fat_pct"),
        bmi=data.get("bmi"),
        waist_cm=data.get("waist_cm")
    )
    return Response(BodyCompositionSerializer(entry).data)

# ═══════════════════════════════════════════════════════════════
# COMPLIANCE MONITORING
# ═══════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_compliance_stats(request, member_id):
    # Habit completion
    logs = HabitLog.objects.filter(member_id=member_id, date__gte=datetime.now(timezone.utc) - timedelta(days=7))
    habit_rate = round(logs.filter(completed=True).count() / max(logs.count(), 1) * 100) if logs.exists() else 75
    
    # Session adherence
    sessions = CCSession.objects.filter(member_id=member_id)
    adherence = round(sessions.filter(status="completed").count() / max(sessions.count(), 1) * 100) if sessions.exists() else 100
    
    return Response({
        "member_id": member_id,
        "habit_completion_rate": habit_rate,
        "session_adherence": adherence,
        "overall_compliance": round((habit_rate + adherence) / 2)
    })

# ═══════════════════════════════════════════════════════════════
# CHALLENGE MANAGEMENT (PFC)
# ═══════════════════════════════════════════════════════════════

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def manage_challenges(request):
    if request.method == 'GET':
        challenges = Challenge.objects.filter(created_by=request.user).order_by("-created_at")
        return Response({"challenges": list(challenges.values())})
    
    data = request.data
    ch = Challenge.objects.create(
        name=data.get("name"),
        description=data.get("description", ""),
        challenge_type=data.get("type", "steps"),
        target_value=data.get("target", 10000),
        duration_days=data.get("duration_days", 7),
        start_date=data.get("start_date", datetime.now(timezone.utc).date()),
        created_by=request.user,
        status="active"
    )
    return Response({"status": "created", "id": ch.id})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_challenge_leaderboard(request, challenge_id):
    ch = get_object_or_404(Challenge, id=challenge_id)
    participants = ChallengeParticipant.objects.filter(challenge=ch).order_by("-progress")
    leaderboard = []
    for p in participants:
        leaderboard.append({
            "member_id": p.user.id,
            "member_name": p.user.get_full_name() or p.user.username,
            "progress": p.progress,
            "rank": 0 # Logic to calculate rank could be added
        })
    return Response({"challenge": {"id": ch.id, "name": ch.name}, "leaderboard": leaderboard})

# ═══════════════════════════════════════════════════════════════
# PSY: Behavioral Tracking & Therapy Programs
# ═══════════════════════════════════════════════════════════════

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def manage_behavior_logs(request, member_id=None):
    if request.method == 'GET':
        logs = BehaviorLog.objects.filter(member_id=member_id).order_by("-date")
        return Response({"entries": BehaviorLogSerializer(logs, many=True).data})
    
    data = request.data
    log = BehaviorLog.objects.create(
        member_id=data.get("member_id"),
        date=data.get("date", datetime.now(timezone.utc).date()),
        mood_score=data.get("mood_score", 5),
        sleep_adherence=data.get("sleep_adherence", False),
        meditation_done=data.get("meditation_done", False),
        screen_time_hrs=data.get("screen_time_hrs"),
        stress_triggers=data.get("stress_triggers", [])
    )
    return Response(BehaviorLogSerializer(log).data)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def manage_therapy_programs(request):
    if request.method == 'GET':
        member_id = request.query_params.get('member_id')
        progs = TherapyProgram.objects.filter(therapist=request.user)
        if member_id:
            progs = progs.filter(member_id=member_id)
        return Response({"programs": TherapyProgramSerializer(progs, many=True).data})
    
    data = request.data
    prog = TherapyProgram.objects.create(
        member_id=data.get("member_id"),
        therapist=request.user,
        name=data.get("name"),
        type=data.get("type", "Stress Management"),
        duration_weeks=data.get("duration_weeks", 8),
        modules=data.get("modules", []),
        goals=data.get("goals", [])
    )
    return Response(TherapyProgramSerializer(prog).data)

# ═══════════════════════════════════════════════════════════════
# NUT: Consultation Notes & Enhanced Meal Plans
# ═══════════════════════════════════════════════════════════════

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def manage_nutrition_notes(request, member_id=None):
    if request.method == 'GET':
        notes = NutritionConsultationNote.objects.filter(member_id=member_id).order_by("-date")
        return Response({"notes": NutritionConsultationNoteSerializer(notes, many=True).data})
    
    data = request.data
    note = NutritionConsultationNote.objects.create(
        member_id=data.get("member_id"),
        nutritionist=request.user,
        dietary_analysis=data.get("dietary_analysis", ""),
        recommendations=data.get("recommendations", ""),
        meal_plan_updates=data.get("meal_plan_updates", ""),
        follow_up_plan=data.get("follow_up_plan", "")
    )
    return Response(NutritionConsultationNoteSerializer(note).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_meal_plan_detail(request, plan_id):
    plan = get_object_or_404(MealPlan, id=plan_id)
    days = MealPlanDay.objects.filter(meal_plan=plan).order_by("day_number")
    return Response({
        "plan": MealPlanSerializer(plan).data,
        "days": MealPlanDaySerializer(days, many=True).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def save_meal_plan_day(request):
    data = request.data
    plan_id = data.get("plan_id")
    plan = get_object_or_404(MealPlan, id=plan_id)
    
    day, created = MealPlanDay.objects.get_or_create(
        meal_plan=plan,
        day_number=data.get("day_number"),
        defaults={
            "meals": data.get("meals", {}),
            "total_calories": data.get("total_calories", 0),
            "total_protein": data.get("total_protein", 0),
            "total_carbs": data.get("total_carbs", 0),
            "total_fat": data.get("total_fat", 0)
        }
    )
    if not created:
        for attr in ["meals", "total_calories", "total_protein", "total_carbs", "total_fat", "notes"]:
            if attr in data:
                setattr(day, attr, data[attr])
        day.save()
        
    return Response(MealPlanDaySerializer(day).data)

# ═══════════════════════════════════════════════════════════════
# COACH PROFILE, PERFORMANCE & ALERTS
# ═══════════════════════════════════════════════════════════════

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def manage_coach_profile(request):
    profile, created = HCPProfile.objects.get_or_create(user=request.user)
    if request.method == 'GET':
        return Response({"profile": HCPProfileSerializer(profile).data})
    
    data = request.data
    for attr in ["specialty", "qualification", "bio", "availability", "notification_prefs"]:
        if attr in data:
            setattr(profile, attr, data[attr])
    profile.save()
    return Response({"status": "updated"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_coach_performance(request):
    # Aggregated KPIs
    assignments = CCAssignment.objects.filter(cc=request.user).count()
    sessions = CCSession.objects.filter(coach=request.user).count()
    goals = Goal.objects.filter(created_by=request.user)
    completed_goals = goals.filter(status="completed").count()
    
    return Response({
        "total_clients": assignments,
        "total_sessions": sessions,
        "goals_created": goals.count(),
        "goals_completed": completed_goals,
        "completion_rate": round(completed_goals / max(goals.count(), 1) * 100),
        "avg_session_compliance": 85 # Placeholder
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_role_alerts(request):
    # Dynamic alert feed
    role = request.user.profile.role.name
    alerts = []
    
    if "psych" in role:
        crisis = CrisisAlert.objects.filter(status="active")
        for c in crisis:
            alerts.append({"type": "crisis", "severity": "CRITICAL", "message": f"Crisis: {c.member.username}", "created_at": c.created_at})
    
    return Response({"alerts": alerts})

# ═══════════════════════════════════════════════════════════════
# ESCALATIONS SYSTEM
# ═══════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def list_escalations(request):
    mode = request.query_params.get('mode', 'received')
    if mode == 'sent':
        escs = Escalation.objects.filter(created_by=request.user)
    else:
        # For simplicity, filter by role/department logic if possible, 
        # or just return all for now
        escs = Escalation.objects.all()
        
    return Response({
        "escalations": EscalationSerializer(escs, many=True).data,
        "stats": {"pending": escs.filter(status="pending").count(), "resolved": escs.filter(status="resolved").count()}
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def respond_to_escalation(request, escalation_id):
    esc = get_object_or_404(Escalation, id=escalation_id)
    esc.status = "resolved"
    esc.resolution_notes = request.data.get("response", "")
    esc.save()
    return Response({"status": "resolved"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_simplified_hps(request, member_id):
    hps = HPSScore.objects.filter(user_id=member_id).first()
    if not hps:
        return Response({"error": "No HPS found"}, status=404)
    return Response({
        "final_score": hps.hps_final,
        "pillars": hps.pillars,
        "last_updated": hps.timestamp
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@coach_auth_check
def get_corporate_wellness_v2(request):
    """B2B wellness stats (Aggregated)."""
    # Simply count total employees and avg HPS for demo
    employees_count = User.objects.filter(profile__role__name="employee").count()
    avg_hps = HPSScore.objects.aggregate(Avg('hps_final'))['hps_final__avg'] or 0
    
    return Response({
        "total_employees": employees_count,
        "avg_hps": round(avg_hps),
        "at_risk_count": HPSScore.objects.filter(hps_final__lt=400).count(),
        "participation_rate": 85 # Placeholder
    })
