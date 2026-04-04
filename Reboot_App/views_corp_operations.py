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
    UserProfile, HPSScore, WellnessProgramme, 
    FranchiseSeason, Company
)
from .views_corp_utils import _req_corp, _tier_str
from .serializers_corp import WellnessProgrammeSerializer, FranchiseSeasonSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profit_share(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    tiers = {"platinum": [], "gold": [], "silver": [], "bronze": [], "ineligible": []}
    for emp in employees:
        latest_hps = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        hps = latest_hps.hps_final if latest_hps else 0
        
        entry = {
            "id": str(emp.id), 
            "name": emp.get_full_name() or emp.username, 
            "department": emp.profile.department.name if emp.profile.department else "Unknown", 
            "hps": hps
        }
        
        if hps >= 900: 
            entry["tier"] = "Platinum"; entry["multiplier"] = 10; tiers["platinum"].append(entry)
        elif hps >= 800: 
            entry["tier"] = "Gold"; entry["multiplier"] = 5; tiers["gold"].append(entry)
        elif hps >= 700: 
            entry["tier"] = "Silver"; entry["multiplier"] = 2.5; tiers["silver"].append(entry)
        elif hps >= 600: 
            entry["tier"] = "Bronze"; entry["multiplier"] = 1; tiers["bronze"].append(entry)
        else: 
            entry["tier"] = "Ineligible"; entry["multiplier"] = 0; tiers["ineligible"].append(entry)
            
    base_payout = 5000
    total_payout = sum(base_payout * e["multiplier"] for t in tiers.values() for e in t if e["multiplier"] > 0)
    eligible_count = sum(len(t) for k, t in tiers.items() if k != "ineligible")
    near_eligible = [e for e in tiers["ineligible"] if e["hps"] >= 550]
    
    return Response({
        "tiers": {k: {"employees": v, "count": len(v)} for k, v in tiers.items()},
        "summary": {
            "total_eligible": eligible_count, 
            "total_ineligible": len(tiers["ineligible"]),
            "near_eligible": len(near_eligible), 
            "total_payout_inr": total_payout, 
            "base_payout_inr": base_payout,
            "cycle_days_remaining": random.randint(30, 150), 
            "cycle_period": "H1 2026 (Jan-Jun)"
        },
        "near_eligible_employees": near_eligible[:15],
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_franchise_status(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    latest_hps_map = {}
    for emp in employees:
        s = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        if s:
            latest_hps_map[emp.id] = s.hps_final
            
    hps_vals = list(latest_hps_map.values())
    avg_hps = round(sum(hps_vals) / len(hps_vals), 1) if hps_vals else 0
    
    dept_league = {}
    for emp in employees:
        dept = emp.profile.department.name if emp.profile.department else "Unknown"
        uid = emp.id
        if dept not in dept_league:
            dept_league[dept] = {"name": dept, "hps_scores": [], "members": 0}
        dept_league[dept]["members"] += 1
        if uid in latest_hps_map:
            dept_league[dept]["hps_scores"].append(latest_hps_map[uid])
            
    league_standings = []
    for d in dept_league.values():
        avg = round(sum(d["hps_scores"]) / len(d["hps_scores"]), 1) if d["hps_scores"] else 0
        league_standings.append({
            "department": d["name"], "members": d["members"], "avg_hps": avg,
            "points": round(avg * d["members"] / 100),
            "qualified_members": sum(1 for h in d["hps_scores"] if h >= 550)
        })
    league_standings.sort(key=lambda x: x["points"], reverse=True)
    for i, s in enumerate(league_standings): s["rank"] = i + 1
    
    striking = [{
        "id": str(emp.id), "name": emp.get_full_name() or emp.username, "hps": latest_hps_map[emp.id],
        "gap": round(550 - latest_hps_map[emp.id], 1)
    } for emp in employees if emp.id in latest_hps_map and 500 <= latest_hps_map[emp.id] < 550]
    striking.sort(key=lambda x: x["gap"])
    
    return Response({
        "season": {
            "name": "Season IV — 2026", "status": "Active", "days_remaining": random.randint(30, 90),
            "qualification_deadline": "2026-06-30"
        },
        "franchise": {
            "avg_hps": avg_hps, "target_hps": 550,
            "qualification_pct": min(round((avg_hps / 550) * 100, 1), 100),
            "ranking": random.randint(1, 25), "total_franchises": 48,
            "qualified_550": sum(1 for h in hps_vals if h >= 550),
            "qualified_600": sum(1 for h in hps_vals if h >= 600), "total_employees": employees.count()
        },
        "dept_league": league_standings, "striking_range": striking[:20],
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_programmes(request):
    _req_corp(request.user)
    if request.method == 'GET':
        programmes = WellnessProgramme.objects.all().order_by('-created_at')
        serializer = WellnessProgrammeSerializer(programmes, many=True)
        return Response({"programmes": serializer.data})
    
    elif request.method == 'POST':
        data = request.data
        prog = WellnessProgramme.objects.create(
            name=data["name"],
            type=data.get("type", "challenge"),
            target_dimension=data.get("target_dimension", ""),
            duration_days=data.get("duration_days", 30),
            status="upcoming",
            reward_healthcoins=data.get("reward_healthcoins", 500),
            created_by=request.user
        )
        serializer = WellnessProgrammeSerializer(prog)
        return Response(serializer.data, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_roi_analytics(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    total = employees.count()
    
    hps_scores = []
    for emp in employees:
        s = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        if s:
            hps_scores.append(s.hps_final)
            
    avg_hps = round(sum(hps_scores) / len(hps_scores), 1) if hps_scores else 0
    annual_investment = total * 12000
    
    absenteeism_reduction_pct = min(round((avg_hps - 400) / 10, 1), 30) if avg_hps > 400 else 0
    productivity_gain_pct = min(round((avg_hps - 450) / 15, 1), 15) if avg_hps > 450 else 0
    
    healthcare_savings = round(total * 3500 * (absenteeism_reduction_pct / 100))
    productivity_value = round(total * 50000 * (productivity_gain_pct / 100))
    total_benefit = healthcare_savings + productivity_value
    
    roi_pct = round(((total_benefit - annual_investment) / annual_investment) * 100, 1) if annual_investment else 0
    
    now = timezone.now()
    monthly_trend = [{
        "month": (now - timedelta(days=30 * (5 - i))).strftime("%b"),
        "investment": round(annual_investment / 12), 
        "savings": round(total_benefit / 12 + random.uniform(-5000, 5000)),
        "avg_hps": round(avg_hps + random.uniform(-15, 15), 1)
    } for i in range(6)]
    
    return Response({
        "roi": {
            "annual_investment_inr": annual_investment, "healthcare_savings_inr": healthcare_savings,
            "productivity_value_inr": productivity_value, "total_benefit_inr": total_benefit, "roi_pct": roi_pct,
            "cost_per_hps_point": round(annual_investment / max(avg_hps, 1))
        },
        "impact": {
            "absenteeism_reduction_pct": absenteeism_reduction_pct,
            "productivity_gain_pct": productivity_gain_pct,
            "profit_share_eligible_pct": round(sum(1 for h in hps_scores if h >= 600) / max(total, 1) * 100, 1)
        },
        "monthly_trend": monthly_trend, "total_employees": total, "avg_hps": avg_hps,
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_seasons(request):
    _req_corp(request.user)
    if request.method == 'GET':
        seasons = FranchiseSeason.objects.all().order_by('-created_at')
        serializer = FranchiseSeasonSerializer(seasons, many=True)
        return Response({"seasons": serializer.data})
    
    elif request.method == 'POST':
        data = request.data
        season = FranchiseSeason.objects.create(
            name=data["name"],
            status=data.get("status", "upcoming"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            qualification_hps=data.get("qualification_hps", 550),
            qualification_pct_required=data.get("qualification_pct_required", 60),
            reward_pool_inr=data.get("reward_pool_inr", 5000000),
            created_by=request.user
        )
        serializer = FranchiseSeasonSerializer(season)
        return Response(serializer.data, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_qualification_tracker(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    milestones = [
        {"name": "Bronze", "hps": 450, "color": "#CD7F32", "reached": 0, "total": 0},
        {"name": "Silver", "hps": 550, "color": "#C0C0C0", "reached": 0, "total": 0},
        {"name": "Gold", "hps": 650, "color": "#FFD700", "reached": 0, "total": 0},
        {"name": "Platinum", "hps": 800, "color": "#C0C0FF", "reached": 0, "total": 0},
    ]
    
    tracker = []
    for emp in employees:
        s = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        hps = s.hps_final if s else 0
        
        emp_milestones = []
        for m in milestones:
            m["total"] += 1
            reached = hps >= m["hps"]
            if reached: m["reached"] += 1
            emp_milestones.append({"name": m["name"], "target": m["hps"], "reached": reached})
        
        next_m = next((em for em in emp_milestones if not em["reached"]), None)
        tracker.append({
            "id": str(emp.id), "name": emp.get_full_name() or emp.username, 
            "department": emp.profile.department.name if emp.profile.department else "Unknown",
            "hps": hps, "milestones": emp_milestones, "next_milestone": next_m,
            "gap": next_m["target"] - hps if next_m else 0, "qualified": hps >= 550
        })
        
    tracker.sort(key=lambda x: x["hps"], reverse=True)
    milestone_summary = [{
        "name": m["name"], "hps": m["hps"], "color": m["color"], "reached": m["reached"],
        "total": m["total"], "pct": round(m["reached"] / max(m["total"], 1) * 100, 1)
    } for m in milestones]
    
    qualified = sum(1 for t in tracker if t["qualified"])
    return Response({
        "employees": tracker, "total": len(tracker), "qualified": qualified,
        "qualification_pct": round(qualified / max(len(tracker), 1) * 100, 1), 
        "milestone_summary": milestone_summary
    })
