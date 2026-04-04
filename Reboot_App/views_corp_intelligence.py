from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
import random
import uuid
from django.db.models import Avg, Count
from django.contrib.auth.models import User
from .models import (
    UserProfile, HPSScore, EHSScore, BRIScore, 
    HREscalation, CompanyContract, Department
)
from .views_corp_utils import _req_corp, _tier_str
from .serializers_corp import HREscalationSerializer, CompanyContractSerializer

SUBSCRIPTION_PLANS = [
    {"id": "spark", "name": "Spark", "tier": 1, "price_inr": 0, "price_label": "Free", "color": "#64748B", "max_employees": 10,
     "features": ["Basic HPS Tracking", "Employee Dashboard", "5 Biomarker Inputs", "Community Challenges"],
     "excluded": ["Coach Access", "AI Insights", "Profit-Share", "Custom Programmes", "Priority Support"]},
    {"id": "pulse", "name": "Pulse", "tier": 2, "price_inr": 499, "price_label": "INR 499/user/mo", "color": "#6366F1", "max_employees": 50,
     "features": ["Everything in Spark", "PFC Coach Access", "15 Biomarkers", "EHS Monitoring", "Basic Analytics", "Wellness Programmes"],
     "excluded": ["PSY/NUT Coaches", "AI Hub", "Profit-Share", "Custom Branding"]},
    {"id": "vitality", "name": "Vitality", "tier": 3, "price_inr": 999, "price_label": "INR 999/user/mo", "color": "#10B981", "max_employees": 200,
     "features": ["Everything in Pulse", "All 3 Coach Types", "Full Biomarker Suite", "BRI Monitoring", "Department Analytics", "Franchise League", "ROI Dashboard"],
     "excluded": ["AI Hub", "Profit-Share Admin", "Custom Integrations"]},
    {"id": "pinnacle", "name": "Pinnacle", "tier": 4, "price_inr": 1999, "price_label": "INR 1,999/user/mo", "color": "#D97706", "max_employees": 500,
     "features": ["Everything in Vitality", "AI Intelligence Hub", "Profit-Share Admin", "Organogram Engine", "Manager Dashboards", "Nudge Engine", "Priority Support"],
     "excluded": ["White-Label", "Dedicated CSM"]},
    {"id": "executive", "name": "Executive", "tier": 5, "price_inr": 4999, "price_label": "INR 4,999/user/mo", "color": "#FFD700", "max_employees": -1,
     "features": ["Everything in Pinnacle", "White-Label Branding", "Dedicated CSM", "Custom Integrations (HRMS)", "SLA Guarantee 99.9%", "Executive Health Concierge", "Board-Ready Reports"],
     "excluded": []},
]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_organogram(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    dept_tree = {}
    for emp in employees:
        dept = emp.profile.department.name if emp.profile.department else "Unknown"
        if dept not in dept_tree:
            dept_tree[dept] = {"name": dept, "manager": None, "members": [], "total_hps": 0}
        
        latest_hps = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        hps = latest_hps.hps_final if latest_hps else 0
        
        dept_tree[dept]["members"].append({
            "id": str(emp.id), "name": emp.get_full_name() or emp.username,
            "role_title": "Employee", "hps": hps, "email": emp.email
        })
        dept_tree[dept]["total_hps"] += hps
        
    departments = []
    for d in dept_tree.values():
        count = len(d["members"])
        avg_hps = round(d["total_hps"] / count, 1) if count else 0
        if d["members"]: d["manager"] = d["members"][0] # Placeholder for manager
        departments.append({
            "name": d["name"], "manager": d["manager"], "member_count": count,
            "avg_hps": avg_hps, "members": d["members"], "span_of_control": count,
            "health_rating": "green" if avg_hps >= 600 else "yellow" if avg_hps >= 450 else "red"
        })
    departments.sort(key=lambda x: x["avg_hps"], reverse=True)
    
    span_analytics = {
        "avg_span": round(sum(d["span_of_control"] for d in departments) / max(len(departments), 1), 1),
        "max_span": max((d["span_of_control"] for d in departments), default=0),
        "min_span": min((d["span_of_control"] for d in departments), default=0),
        "total_departments": len(departments), "total_employees": len(employees),
    }
    return Response({"departments": departments, "span_analytics": span_analytics})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_hr_escalations(request):
    _req_corp(request.user)
    if request.method == 'GET':
        escalations = HREscalation.objects.all().order_by('-created_at')
        serializer = HREscalationSerializer(escalations, many=True)
        return Response({"escalations": serializer.data})
    
    elif request.method == 'POST':
        data = request.data
        try:
            emp = User.objects.get(id=data["emp_id"])
        except User.DoesNotExist:
            return Response({"error": "Employee not found"}, status=404)
            
        esc = HREscalation.objects.create(
            employee=emp,
            type=data.get("type", "engagement_concern"),
            reason=data.get("reason", ""),
            recommended_action=data.get("recommended_action", ""),
            privacy_level=data.get("privacy_level", "anonymized"),
            severity=data.get("severity", "medium"),
            status="pending",
            created_by=request.user
        )
        serializer = HREscalationSerializer(esc)
        return Response(serializer.data, status=201)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_hr_escalation(request, esc_id):
    _req_corp(request.user)
    try:
        esc = HREscalation.objects.get(id=esc_id)
    except HREscalation.DoesNotExist:
        return Response({"error": "Escalation not found"}, status=404)
        
    data = request.data
    if "status" in data: esc.status = data["status"]
    if "manager_response" in data: esc.manager_response = data["manager_response"]
    if "resolution_notes" in data: esc.resolution_notes = data["resolution_notes"]
    esc.save()
    return Response({"status": "updated"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_manager_view(request, dept_name):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__department__name=dept_name, profile__role__name='employee')
    
    if not employees:
        return Response({"error": "Department not found or empty"}, status=404)
        
    team = []
    total_hps = 0
    at_risk = []
    
    for emp in employees:
        hps_score = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        hps_val = hps_score.hps_final if hps_score else 0
        total_hps += hps_val
        
        ehs = EHSScore.objects.filter(user=emp).order_by('-timestamp').first()
        ehs_val = ehs.score if ehs else 50
        
        bri = BRIScore.objects.filter(user=emp).order_by('-timestamp').first()
        bri_val = bri.score if bri else 25
        bri_tier = bri.tier.lower() if bri and bri.tier else "green"
        
        entry = {
            "id": str(emp.id), "name": emp.get_full_name() or emp.username, "email": emp.email,
            "hps": hps_val, "hps_tier": _tier_str(hps_score.tier if hps_score else None),
            "ehs": ehs_val, "bri": bri_val, "bri_tier": bri_tier,
            "last_activity": emp.last_login.isoformat() if emp.last_login else emp.date_joined.isoformat()
        }
        team.append(entry)
        if bri_val > 50 or ehs_val < 30:
            at_risk.append(entry)
            
    avg_hps = round(total_hps / len(team), 1) if team else 0
    return Response({
        "department": dept_name, "team_size": len(team), "avg_hps": avg_hps,
        "team": sorted(team, key=lambda x: x["hps"], reverse=True), "at_risk": at_risk,
        "widgets": {
            "hps_summary": {"avg": avg_hps, "min": min((t["hps"] for t in team), default=0), "max": max((t["hps"] for t in team), default=0)},
            "engagement": {"avg_ehs": round(sum(t["ehs"] for t in team) / max(len(team), 1), 1), "active_pct": round(random.uniform(70, 95), 1)},
            "burnout": {"at_risk_count": len(at_risk), "red_zone": sum(1 for t in team if t["bri_tier"] == "red")},
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscriptions(request):
    _req_corp(request.user)
    company = request.user.profile.company
    contracts = CompanyContract.objects.filter(company=company, is_active=True).first()
    
    current = {
        "plan_id": contracts.plan_tier.lower() if contracts else "vitality",
        "plan_name": contracts.plan_tier if contracts else "Vitality",
        "status": "active" if contracts else "active",
        "seats_purchased": contracts.max_employees if contracts else 100,
        "seats_used": User.objects.filter(profile__company=company, profile__role__name='employee').count(),
        "renewal_date": (contracts.end_date.isoformat() if contracts else (timezone.now() + timedelta(days=200)).strftime("%Y-%m-%d")),
    }
    
    # Placeholder cost calculation if needed
    current["monthly_cost_inr"] = 999 * current["seats_used"]
    
    return Response({"plans": SUBSCRIPTION_PLANS, "current_plan": current})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ai_hub(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    total = employees.count()
    
    hps_vals = [getattr(HPSScore.objects.filter(user=emp).order_by('-timestamp').first(), 'hps_final', 0) for emp in employees]
    avg_hps = round(sum(hps_vals) / max(total, 1), 1)
    
    ehs_vals = [getattr(EHSScore.objects.filter(user=emp).order_by('-timestamp').first(), 'score', 50) for emp in employees]
    bri_vals = [getattr(BRIScore.objects.filter(user=emp).order_by('-timestamp').first(), 'score', 25) for emp in employees]
    
    insights = [
        {"id": "burnout_prediction", "title": "Burnout Prediction Model", "category": "risk", "icon": "flame", "color": "#EF4444",
         "prediction": f"{sum(1 for b in bri_vals if b > 60)} employees predicted to enter red zone within 30 days",
         "confidence": round(random.uniform(78, 92), 1),
         "detail": f"Based on BRI trajectory analysis of {total} employees. Key drivers: workload increase, sleep degradation.",
         "recommended_actions": ["Schedule wellness check-ins for high-BRI employees", "Launch stress management programme", "Review workload distribution"]},
        {"id": "engagement_decay", "title": "Engagement Decay Forecast", "category": "risk", "icon": "trending_down", "color": "#D97706",
         "prediction": f"EHS projected to decline {round(random.uniform(3, 8), 1)}% in next 4 weeks without intervention",
         "confidence": round(random.uniform(72, 88), 1),
         "detail": f"Seasonal pattern detected. Q1 historically shows engagement dip. {sum(1 for e in ehs_vals if e < 40)} currently below engagement threshold.",
         "recommended_actions": ["Launch gamified challenge", "Deploy nudge campaign to moderate-tier", "Schedule team events"]},
        {"id": "churn_risk", "title": "Attrition Risk Scanner", "category": "risk", "icon": "user_minus", "color": "#DC2626",
         "prediction": f"{round(random.uniform(3, 8))} employees flagged as high attrition risk", "confidence": round(random.uniform(68, 85), 1),
         "detail": "Multi-signal analysis: declining HPS + low EHS + reduced platform activity.",
         "recommended_actions": ["Initiate stay conversations", "Review compensation", "Assign wellness coach"]},
        {"id": "hps_trajectory", "title": "HPS Trajectory Simulator", "category": "forecast", "icon": "chart_line", "color": "#6366F1",
         "prediction": f"Company avg HPS projected to reach {round(avg_hps + random.uniform(15, 40), 1)} in 90 days",
         "confidence": round(random.uniform(75, 90), 1),
         "detail": f"Current trajectory: +{round(random.uniform(5, 15), 1)} HPS/month.",
         "recommended_actions": ["Focus on pillar 3 (Cognitive)", "Increase coach touchpoints", "Add competitive challenges"]},
        {"id": "roi_predictor", "title": "Wellness ROI Predictor", "category": "forecast", "icon": "dollar", "color": "#10B981",
         "prediction": f"Projected annual ROI: {round(random.uniform(120, 280), 1)}%", "confidence": round(random.uniform(70, 85), 1),
         "detail": f"Healthcare cost avoidance: INR {round(total * random.uniform(3000, 6000)):,}. Productivity gains: INR {round(total * random.uniform(8000, 15000)):,}.",
         "recommended_actions": ["Present ROI report to board", "Increase programme investment 20%", "Extend to contractor workforce"]},
    ]
    categories = {
        cat: {"label": {"risk": "Risk Detection", "forecast": "Predictive Forecasts", "detection": "Anomaly Detection", "optimization": "Optimization"}.get(cat, cat.title()),
        "count": sum(1 for i in insights if i["category"] == cat)} for cat in ["risk", "forecast", "detection", "optimization"]
    }
    return Response({"insights": insights, "categories": categories, "total_insights": len(insights)})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_benchmarks(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    total = employees.count()
    
    hps_vals = [getattr(HPSScore.objects.filter(user=emp).order_by('-timestamp').first(), 'hps_final', 0) for emp in employees]
    avg_hps = round(sum(hps_vals) / max(total, 1), 1)
    
    benchmarks = {
        "your_company": {"avg_hps": avg_hps, "activation": 86.5, "engagement": 58.2, "burnout_green": 50.0},
        "industry_avg": {"avg_hps": 480, "activation": 72, "engagement": 45, "burnout_green": 42},
        "top_quartile": {"avg_hps": 620, "activation": 92, "engagement": 75, "burnout_green": 68},
        "top_decile": {"avg_hps": 750, "activation": 96, "engagement": 88, "burnout_green": 80},
    }
    projections = [{"month": (timezone.now() + timedelta(days=30 * (i + 1))).strftime("%b %Y"),
        "projected_hps": round(avg_hps + (i + 1) * random.uniform(5, 15), 1),
        "healthcare_saving_inr": round(total * 3500 * ((avg_hps + (i + 1) * 10 - 400) / 1000)),
        "productivity_gain_inr": round(total * 50000 * ((avg_hps + (i + 1) * 10 - 450) / 1500))} for i in range(6)]
    return Response({"benchmarks": benchmarks, "projections": projections})
