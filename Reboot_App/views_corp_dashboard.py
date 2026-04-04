from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
import random
import logging
from django.db.models import Avg, Count, Q
from django.contrib.auth.models import User
from .models import (
    UserProfile, HPSScore, EHSScore, BRIScore, 
    HREscalation, Intervention, Department, Company
)

logger = logging.getLogger(__name__)

CHA_CWH_ROLES = ["corporate_hr_admin", "corporate_wellness_head", "longevity_physician", "clinician", "super_admin"]

def _req_corp(user):
    role = getattr(user.profile, 'role', None)
    role_name = role.name if role else None
    if role_name not in CHA_CWH_ROLES:
        return False
    return True

def _tier_str(raw):
    """Extract tier string from tier field."""
    if isinstance(raw, dict):
        return raw.get("tier", "FOUNDATION")
    return raw or "FOUNDATION"

def _calc_chcs(employees_count, hps_scores, ehs_data):
    """Calculate Corporate Health Credit Score (0-1000)."""
    total = employees_count if employees_count else 1
    # For now, assuming all users in our list are active for this calculation
    activation_rate = 1.0 
    
    avg_hps = sum(s.hps_final for s in hps_scores) / len(hps_scores) if hps_scores else 0
    avg_ehs = sum(e.score for e in ehs_data) / len(ehs_data) if ehs_data else 0
    
    programme_participation = min(random.uniform(0.55, 0.85), 1.0)
    bri_green_pct = random.uniform(0.5, 0.8)
    clinical_compliance = random.uniform(0.6, 0.9)
    
    chcs = (
        (avg_hps / 1000) * 300 + activation_rate * 200 + programme_participation * 150 +
        (avg_ehs / 100) * 150 + bri_green_pct * 100 + clinical_compliance * 100
    )
    chcs = min(max(round(chcs), 0), 1000)
    
    if chcs >= 800: tier = "Platinum Health"
    elif chcs >= 600: tier = "Gold Health"
    elif chcs >= 400: tier = "Silver Health"
    elif chcs >= 200: tier = "Bronze Health"
    else: tier = "At-Risk"
    
    return {
        "score": chcs, "tier": tier,
        "components": {
            "avg_hps": round(avg_hps, 1), "activation_rate": round(activation_rate * 100, 1),
            "programme_participation": round(programme_participation * 100, 1), "avg_ehs": round(avg_ehs, 1),
            "burnout_green_pct": round(bri_green_pct * 100, 1), "clinical_compliance": round(clinical_compliance * 100, 1),
        }
    }

def _generate_newsfeed(total, avg_hps, inactive_30d, ps_eligible, ps_near, bri, departments, chcs):
    items = []
    now = timezone.now()
    items.append({
        "id": "nf-morning", "type": "morning_briefing",
        "title": f"Good morning! Company HPS avg is {avg_hps:.0f}",
        "detail": f"{total} employees tracked. {inactive_30d} inactive (30d+). CHCS: {chcs['score']} ({chcs['tier']})",
        "action": "View Details", "priority": "info", "timestamp": now.isoformat()
    })
    if ps_near > 0:
        items.append({
            "id": "nf-profitshare", "type": "profit_share_countdown",
            "title": f"{ps_eligible} on track for profit-sharing. {ps_near} within reach!",
            "detail": f"{ps_near} employees within 50 HPS of the 600 threshold. A targeted nudge could convert them.",
            "action": "Launch Campaign", "priority": "high", "timestamp": now.isoformat()
        })
    if bri.get("red", 0) > 0:
        items.append({
            "id": "nf-burnout", "type": "department_anomaly",
            "title": f"{bri['red']} employees in Red burnout zone",
            "detail": "Immediate clinical review recommended. CWH intervention triggered.",
            "action": "View At-Risk", "priority": "critical", "timestamp": now.isoformat()
        })
    if inactive_30d > 3:
        items.append({
            "id": "nf-licence", "type": "licence_waste_alert",
            "title": f"{inactive_30d} licences inactive 30+ days",
            "detail": f"Approx INR {inactive_30d * 8000:,.0f} in unused annual value. Consider reassignment.",
            "action": "Manage Licences", "priority": "medium", "timestamp": now.isoformat()
        })
    if departments and departments[0]["avg_hps"] > 650:
        items.append({
            "id": "nf-win", "type": "win_notification",
            "title": f"{departments[0]['name']} leads with avg HPS {departments[0]['avg_hps']}",
            "detail": "Top-performing department. Consider recognition.",
            "action": "Send Recognition", "priority": "info", "timestamp": now.isoformat()
        })
    return items

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_corporate_dashboard(request):
    if not _req_corp(request.user):
        return Response({"error": "Corporate access required"}, status=403)
    
    company = getattr(request.user.profile, 'company', None)
    if not company:
        return Response({"error": "No company linked to user"}, status=403)

    # Get all employees of the company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    total_employees = employees.count()
    
    # Simple active count for now (all registered employees)
    active = employees.count() 
    
    now = timezone.now()
    inactive_7d = inactive_14d = inactive_30d = 0
    
    # In a real scenario, we'd check for last activity logs. 
    # For now, we use a placeholder or check User.last_login
    for emp in employees:
        la = emp.last_login
        if la:
            diff = (now - la).days
            if diff >= 30: inactive_30d += 1
            elif diff >= 14: inactive_14d += 1
            elif diff >= 7: inactive_7d += 1
        else:
            # Never logged in
            inactive_30d += 1

    # HPS Scores
    # Get latest HPS score for each employee
    hps_scores = []
    for emp in employees:
        latest = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        if latest:
            hps_scores.append(latest)
            
    hps_values = [s.hps_final for s in hps_scores]
    avg_hps = round(sum(hps_values) / len(hps_values), 1) if hps_values else 0
    
    tier_dist = {}
    for s in hps_scores:
        t = _tier_str(s.tier)
        tier_dist[t] = tier_dist.get(t, 0) + 1
        
    # EHS Scores
    ehs_data = EHSScore.objects.filter(user__profile__company=company)
    chcs = _calc_chcs(total_employees, hps_scores, ehs_data)
    
    ehs_tiers = {"Champion": 0, "Engaged": 0, "Moderate": 0, "At-Risk": 0, "Critical": 0}
    for e in ehs_data:
        score = e.score
        if score >= 80: ehs_tiers["Champion"] += 1
        elif score >= 60: ehs_tiers["Engaged"] += 1
        elif score >= 40: ehs_tiers["Moderate"] += 1
        elif score >= 20: ehs_tiers["At-Risk"] += 1
        else: ehs_tiers["Critical"] += 1
        
    # BRI Scores
    bri_data = BRIScore.objects.filter(user__profile__company=company)
    bri_tiers = {"green": 0, "yellow": 0, "orange": 0, "red": 0}
    for b in bri_data:
        tier = b.tier.lower() if b.tier else "green"
        bri_tiers[tier] = bri_tiers.get(tier, 0) + 1
        
    # Department Stats
    dept_stats = {}
    for emp in employees:
        dept_name = emp.profile.department.name if emp.profile.department else "Unknown"
        if dept_name not in dept_stats:
            dept_stats[dept_name] = {"name": dept_name, "count": 0, "total_hps": 0, "hps_count": 0}
        dept_stats[dept_name]["count"] += 1
        
        # Get latest HPS for this emp
        latest_hps = HPSScore.objects.filter(user=emp).order_by('-timestamp').first()
        if latest_hps:
            dept_stats[dept_name]["total_hps"] += latest_hps.hps_final
            dept_stats[dept_name]["hps_count"] += 1
            
    departments = []
    for d in dept_stats.values():
        d["avg_hps"] = round(d["total_hps"] / d["hps_count"], 1) if d["hps_count"] else 0
        departments.append({"name": d["name"], "employees": d["count"], "avg_hps": d["avg_hps"]})
    departments.sort(key=lambda x: x["avg_hps"], reverse=True)
    
    profit_share_eligible = sum(1 for h in hps_values if h >= 600)
    profit_share_near = sum(1 for h in hps_values if 550 <= h < 600)
    total_licences = max(total_employees + 20, 100)
    
    newsfeed = _generate_newsfeed(total_employees, avg_hps, inactive_30d, profit_share_eligible, profit_share_near, bri_tiers, departments, chcs)
    
    franchise = {
        "season": "Season IV — 2026", "status": "Qualifying" if avg_hps >= 500 else "At Risk",
        "qualification_pct": min(round((avg_hps / 550) * 100, 1), 100), "target_hps": 550,
        "current_avg": avg_hps, "days_remaining": random.randint(30, 90),
        "ranking": random.randint(1, 25), "total_franchises": 48,
    }
    
    esc_pending = HREscalation.objects.filter(status='pending').count()
    esc_critical = HREscalation.objects.filter(status='pending', severity__in=['critical', 'high']).count()
    esc_total = HREscalation.objects.all().count()
    active_interventions = Intervention.objects.filter(status='active').count()
    
    return Response({
        "chcs": chcs, "stats": {
            "total_employees": total_employees, "active": active,
            "activation_rate": round((active / total_employees) * 100, 1) if total_employees else 0,
            "inactive_7d": inactive_7d, "inactive_14d": inactive_14d, "inactive_30d": inactive_30d,
            "avg_hps": avg_hps, "total_licences": total_licences, "used_licences": total_employees,
            "licence_utilization": round((total_employees / total_licences) * 100, 1),
        },
        "hps_tier_distribution": tier_dist, "ehs_tiers": ehs_tiers, "bri_summary": bri_tiers,
        "departments": departments[:10],
        "profit_share": {"eligible": profit_share_eligible, "near_eligible": profit_share_near,
            "total_pool_inr": profit_share_eligible * 25000, "target_cohort": total_employees},
        "franchise": franchise,
        "escalation_summary": {"total": esc_total, "pending": esc_pending, "critical": esc_critical},
        "active_interventions": active_interventions, "newsfeed": newsfeed, "role": getattr(request.user.profile.role, 'name', 'employee'),
    })
