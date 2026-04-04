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
    Intervention, BiomarkerResult, Department
)
from .views_corp_utils import _req_corp, _tier_str

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_employees(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    result = []
    for emp in employees:
        # Latest HPS
        latest_hps = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        # Latest EHS
        latest_ehs = EHSScore.objects.filter(user=emp).order_by('-timestamp').first()
        # Latest BRI
        latest_bri = BRIScore.objects.filter(user=emp).order_by('-timestamp').first()
        
        result.append({
            "id": str(emp.id), 
            "name": emp.get_full_name() or emp.username, 
            "email": emp.email,
            "department": emp.profile.department.name if emp.profile.department else "Unknown", 
            "role_title": "Employee",
            "location": emp.profile.location.name if emp.profile.location else "", 
            "age": emp.profile.age or 0,
            "sex": emp.profile.gender or "",
            "joined_at": emp.date_joined.isoformat(), 
            "activation_status": "active",
            "last_activity": emp.last_login.isoformat() if emp.last_login else emp.date_joined.isoformat(),
            "hps_score": latest_hps.hps_final if latest_hps else 0, 
            "hps_tier": _tier_str(latest_hps.tier if latest_hps else None),
            "ehs_score": latest_ehs.score if latest_ehs else 50, 
            "ehs_tier": latest_ehs.tier if latest_ehs else "Moderate",
            "bri_score": latest_bri.score if latest_bri else 25, 
            "bri_tier": latest_bri.tier if latest_bri else "green",
            "profit_share_eligible": (latest_hps.hps_final >= 600) if latest_hps else False,
        })
    
    result.sort(key=lambda x: x["hps_score"], reverse=True)
    return Response({"employees": result, "total": len(result)})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_employee_detail(request, emp_id):
    _req_corp(request.user)
    try:
        emp = User.objects.get(id=emp_id, profile__role__name='employee')
    except User.DoesNotExist:
        return Response({"error": "Employee not found"}, status=404)
        
    hps_history = HPSScore.objects.filter(user=emp).order_by('-timestamp')[:50]
    latest_ehs = EHSScore.objects.filter(user=emp).order_by('-timestamp').first()
    latest_bri = BRIScore.objects.filter(user=emp).order_by('-timestamp').first()
    biomarkers = BiomarkerResult.objects.filter(user=emp).order_by('-collected_at')[:50]
    
    latest_hps = hps_history[0] if hps_history else None
    
    return Response({
        "employee": {
            "id": str(emp.id),
            "name": emp.get_full_name() or emp.username,
            "email": emp.email,
            "department": emp.profile.department.name if emp.profile.department else "Unknown",
            "location": emp.profile.location.name if emp.profile.location else "",
            "age": emp.profile.age or 0,
            "sex": emp.profile.gender or "",
            "employment_type": emp.profile.employment_type or "full_time",
            "joined_at": emp.date_joined.isoformat(),
        },
        "hps": {
            "current": latest_hps.hps_final if latest_hps else 0, 
            "tier": _tier_str(latest_hps.tier if latest_hps else None),
            "pillars": latest_hps.pillars if latest_hps else {},
            "history": [{"date": h.timestamp.isoformat(), "score": h.hps_final} for h in hps_history[:30]]
        },
        "ehs": {
            "score": latest_ehs.score if latest_ehs else 50,
            "tier": latest_ehs.tier if latest_ehs else "Moderate"
        },
        "bri": {
            "score": latest_bri.score if latest_bri else 25,
            "tier": latest_bri.tier if latest_bri else "green"
        },
        "biomarkers": [{
            "biomarker_code": b.biomarker.code,
            "name": b.biomarker.name,
            "value": b.value,
            "unit": b.biomarker.unit,
            "flag": b.flag,
            "collected_at": b.collected_at.isoformat()
        } for b in biomarkers[:20]],
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_engagement_overview(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    tiers = {"Champion": 0, "Engaged": 0, "Moderate": 0, "At-Risk": 0, "Critical": 0}
    dept_engagement = {}
    all_scores = []
    
    for emp in employees:
        ehs = EHSScore.objects.filter(user=emp).order_by('-timestamp').first()
        score = ehs.score if ehs else 50
        tier = ehs.tier if ehs else "Moderate"
        
        if tier in tiers:
            tiers[tier] += 1
        all_scores.append(score)
        
        dept = emp.profile.department.name if emp.profile.department else "Unknown"
        if dept not in dept_engagement:
            dept_engagement[dept] = {"name": dept, "scores": [], "count": 0}
        dept_engagement[dept]["scores"].append(score)
        dept_engagement[dept]["count"] += 1
        
    dept_heatmap = []
    for d in dept_engagement.values():
        avg = round(sum(d["scores"]) / len(d["scores"]), 1) if d["scores"] else 0
        dept_heatmap.append({
            "department": d["name"], "avg_ehs": avg, "employee_count": d["count"],
            "champions": sum(1 for s in d["scores"] if s >= 80), 
            "critical": sum(1 for s in d["scores"] if s < 20),
            "participation_rate": round(random.uniform(0.6, 0.95) * 100, 1)
        })
    dept_heatmap.sort(key=lambda x: x["avg_ehs"], reverse=True)
    
    avg_ehs = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    now = timezone.now()
    trend = [{"week": (now - timedelta(weeks=11 - i)).strftime("%Y-%m-%d"),
              "avg_ehs": round(avg_ehs + random.uniform(-5, 5), 1)} for i in range(12)]
              
    return Response({
        "avg_ehs": avg_ehs, 
        "total_employees": len(employees), 
        "tier_distribution": tiers,
        "department_heatmap": dept_heatmap, 
        "weekly_trend": trend
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_inactive_employees(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    now = timezone.now()
    inactive = {"7d": [], "14d": [], "30d": []}
    
    for emp in employees:
        last_act_dt = emp.last_login or emp.date_joined
        diff = (now - last_act_dt).days
        
        entry = {
            "id": str(emp.id), 
            "name": emp.get_full_name() or emp.username, 
            "department": emp.profile.department.name if emp.profile.department else "Unknown",
            "days_inactive": diff, 
            "last_activity": last_act_dt.isoformat(), 
            "email": emp.email
        }
        
        if diff >= 30: inactive["30d"].append(entry)
        elif diff >= 14: inactive["14d"].append(entry)
        elif diff >= 7: inactive["7d"].append(entry)
            
    return Response({
        "inactive_7d": inactive["7d"], 
        "inactive_14d": inactive["14d"], 
        "inactive_30d": inactive["30d"],
        "total_inactive": len(inactive["7d"]) + len(inactive["14d"]) + len(inactive["30d"])
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_burnout_overview(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    tiers = {"green": 0, "yellow": 0, "orange": 0, "red": 0}
    dept_burnout = {}
    at_risk = []
    
    for emp in employees:
        bri = BRIScore.objects.filter(user=emp).order_by('-timestamp').first()
        score = bri.score if bri else random.randint(10, 40)
        tier = bri.tier.lower() if bri and bri.tier else "green"
        
        if tier in tiers:
            tiers[tier] += 1
            
        dept = emp.profile.department.name if emp.profile.department else "Unknown"
        if dept not in dept_burnout:
            dept_burnout[dept] = {"name": dept, "scores": [], "red": 0, "orange": 0}
        dept_burnout[dept]["scores"].append(score)
        
        if tier == "red": dept_burnout[dept]["red"] += 1
        elif tier == "orange": dept_burnout[dept]["orange"] += 1
        
        if tier in ("red", "orange"):
            at_risk.append({
                "id": str(emp.id), "name": emp.get_full_name() or emp.username, "department": dept,
                "bri_score": score, "bri_tier": tier,
                "physiological": getattr(bri, 'physiological', round(random.uniform(20, 80), 1)),
                "behavioural": getattr(bri, 'behavioural', round(random.uniform(20, 80), 1)),
                "psychological": getattr(bri, 'psychological', round(random.uniform(20, 80), 1)),
                "organisational": getattr(bri, 'organisational', round(random.uniform(10, 60), 1))
            })
            
    dept_list = []
    for d in dept_burnout.values():
        avg = round(sum(d["scores"]) / len(d["scores"]), 1) if d["scores"] else 0
        dept_list.append({
            "department": d["name"], "avg_bri": avg, "red_count": d["red"],
            "orange_count": d["orange"], "total": len(d["scores"])
        })
    dept_list.sort(key=lambda x: x["avg_bri"], reverse=True)
    
    now = timezone.now()
    trend = [{"week": (now - timedelta(weeks=11 - i)).strftime("%Y-%m-%d"),
              "green": tiers["green"] + random.randint(-3, 3), 
              "yellow": tiers["yellow"] + random.randint(-2, 2),
              "orange": tiers["orange"] + random.randint(-1, 1), 
              "red": max(0, tiers["red"] + random.randint(-1, 1))} for i in range(12)]
              
    at_risk.sort(key=lambda x: x["bri_score"], reverse=True)
    return Response({
        "tier_distribution": tiers, 
        "department_burnout": dept_list, 
        "at_risk_employees": at_risk[:20],
        "total_at_risk": len(at_risk), 
        "weekly_trend": trend
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_intervention(request):
    _req_corp(request.user)
    data = request.data
    
    try:
        emp = User.objects.get(id=data["emp_id"])
    except User.DoesNotExist:
        return Response({"error": "Employee not found"}, status=404)
        
    intervention = Intervention.objects.create(
        employee=emp,
        type=data.get("type", "wellness_program"),
        description=data.get("description", ""),
        assigned_to=User.objects.filter(id=data.get("assigned_to")).first() or request.user,
        assigned_by=request.user,
        status="active"
    )
    
    Notification.objects.create(
        user=emp,
        type="intervention",
        message=f"A new wellness intervention has been initiated for you: {data.get('description', '')}",
        data={
            "title": "New Wellness Intervention",
            "category": "intervention",
            "source": "corporate",
            "intervention_id": str(intervention.id)
        }
    )
    
    return Response({
        "id": str(intervention.id),
        "emp_id": str(emp.id),
        "type": intervention.type,
        "status": intervention.status,
        "created_at": intervention.created_at.isoformat()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_department_analytics(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    dept_data = {}
    for emp in employees:
        dept = emp.profile.department.name if emp.profile.department else "Unknown"
        uid = str(emp.id)
        if dept not in dept_data:
            dept_data[dept] = {
                "name": dept, "employees": [], "hps_scores": [], "ehs_scores": [], "bri_scores": [],
                "tier_dist": {}, "profit_share_eligible": 0
            }
            
        latest_hps = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        latest_ehs = EHSScore.objects.filter(user=emp).order_by('-timestamp').first()
        latest_bri = BRIScore.objects.filter(user=emp).order_by('-timestamp').first()
        
        dept_data[dept]["employees"].append(uid)
        
        hps_val = latest_hps.hps_final if latest_hps else 0
        if hps_val:
            dept_data[dept]["hps_scores"].append(hps_val)
            tier = _tier_str(latest_hps.tier if latest_hps else None)
            dept_data[dept]["tier_dist"][tier] = dept_data[dept]["tier_dist"].get(tier, 0) + 1
            if hps_val >= 600: 
                dept_data[dept]["profit_share_eligible"] += 1
                
        dept_data[dept]["ehs_scores"].append(latest_ehs.score if latest_ehs else 50)
        dept_data[dept]["bri_scores"].append(latest_bri.score if latest_bri else 25)
        
    departments = []
    for d in dept_data.values():
        departments.append({
            "name": d["name"], "employee_count": len(d["employees"]),
            "avg_hps": round(sum(d["hps_scores"]) / len(d["hps_scores"]), 1) if d["hps_scores"] else 0,
            "avg_ehs": round(sum(d["ehs_scores"]) / len(d["ehs_scores"]), 1) if d["ehs_scores"] else 0,
            "avg_bri": round(sum(d["bri_scores"]) / len(d["bri_scores"]), 1) if d["bri_scores"] else 0,
            "hps_tier_distribution": d["tier_dist"], 
            "profit_share_eligible": d["profit_share_eligible"],
            "participation_rate": round(random.uniform(0.65, 0.95) * 100, 1),
            "activation_rate": round(random.uniform(0.8, 0.98) * 100, 1),
        })
    departments.sort(key=lambda x: x["avg_hps"], reverse=True)
    return Response({"departments": departments})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_outliers(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    outliers = []
    for emp in employees:
        latest_hps = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        latest_ehs = EHSScore.objects.filter(user=emp).order_by('-timestamp').first()
        latest_bri = BRIScore.objects.filter(user=emp).order_by('-timestamp').first()
        
        reasons = []
        risk_score = 0
        hps_val = latest_hps.hps_final if latest_hps else 0
        ehs_val = latest_ehs.score if latest_ehs else 50
        bri_val = latest_bri.score if latest_bri else 25
        
        if hps_val > 0 and hps_val < 400: 
            reasons.append(f"Low HPS: {hps_val:.0f}")
            risk_score += 30
        if ehs_val < 30: 
            reasons.append(f"Critical EHS: {ehs_val:.0f}")
            risk_score += 25
        if bri_val > 60: 
            reasons.append(f"High BRI: {bri_val:.0f} ({latest_bri.tier if latest_bri else 'yellow'})")
            risk_score += 25
        if 0 < hps_val < 500: risk_score += 10
        if ehs_val < 40: risk_score += 10
        
        if risk_score >= 25:
            outliers.append({
                "id": str(emp.id), "name": emp.get_full_name() or emp.username, 
                "department": emp.profile.department.name if emp.profile.department else "Unknown",
                "hps_score": hps_val, 
                "hps_tier": _tier_str(latest_hps.tier if latest_hps else None), 
                "ehs_score": ehs_val,
                "bri_score": bri_val, 
                "bri_tier": latest_bri.tier if latest_bri else "green",
                "risk_score": min(risk_score, 100), 
                "reasons": reasons, 
                "intervention_status": "none"
            })
            
    outliers.sort(key=lambda x: x["risk_score"], reverse=True)
    return Response({"outliers": outliers, "total": len(outliers)})
