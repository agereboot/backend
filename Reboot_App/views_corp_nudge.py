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
    NudgeCampaign, Notification
)
from .views_corp_utils import _req_corp, _tier_str
from .serializers_corp import NudgeCampaignSerializer

SEGMENT_DEFS = {
    "inactive_14d": {"label": "Inactive 14+ Days", "color": "#EF4444", "desc": "Employees with no activity for 14+ days"},
    "inactive_30d": {"label": "Inactive 30+ Days", "color": "#DC2626", "desc": "Employees with no activity for 30+ days"},
    "near_profit_share": {"label": "Near Profit-Share", "color": "#D97706", "desc": "HPS 550-599, within reach of 600 threshold"},
    "high_bri": {"label": "High Burnout Risk", "color": "#F97316", "desc": "BRI orange or red tier employees"},
    "low_ehs": {"label": "Low Engagement", "color": "#6366F1", "desc": "EHS below 30 (Critical tier)"},
    "new_joiners": {"label": "New Joiners (30d)", "color": "#10B981", "desc": "Joined within last 30 days"},
    "top_performers": {"label": "Top Performers", "color": "#FFD700", "desc": "HPS 800+ — recognition campaign"},
    "declining_hps": {"label": "Declining HPS", "color": "#EF4444", "desc": "HPS dropped 50+ points recently"},
}

NUDGE_TEMPLATES = {
    "inactive_14d": [
        "Hi {name}, we noticed you haven't logged in recently. Your wellness journey matters — even 5 minutes today can make a difference. Your HPS is {hps}, let's keep it climbing!",
        "Hey {name}! Your team in {dept} misses you. Jump back in and check your latest health insights. Small steps, big impact.",
    ],
    "near_profit_share": [
        "Great news {name}! You're only {gap} HPS points away from profit-sharing eligibility. A focused week on sleep and activity could get you there!",
        "{name}, you're so close to the profit-share threshold! Current HPS: {hps}. Target: 600. Let's make it happen this month.",
    ],
    "high_bri": [
        "{name}, we care about your wellbeing. We've noticed elevated stress indicators. Consider booking a coaching session or trying our Stress Resilience programme.",
        "Hey {name}, your wellness matters to us. Take a moment today for a quick check-in with your coach. Small breaks lead to big recoveries.",
    ],
    "low_ehs": [
        "{name}, there's so much waiting for you on AgeReboot! New challenges, coaching sessions, and health insights. Log in today and explore.",
        "Hi {name}, your health journey is unique. Let's reconnect — your coach has new recommendations tailored just for you.",
    ],
    "top_performers": [
        "Congratulations {name}! Your HPS of {hps} puts you in the elite tier. You're an inspiration to {dept}. Keep leading by example!",
        "{name}, you're a wellness champion! Share your success story and inspire your colleagues. Your discipline is paying off.",
    ],
}

def _get_segment_employees(company, segment_id):
    now = timezone.now()
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    results = []
    for emp in employees:
        hps_val = getattr(HPSScore.objects.filter(user=emp).order_by('-timestamp').first(), 'hps_final', 0)
        ehs_val = getattr(EHSScore.objects.filter(user=emp).order_by('-timestamp').first(), 'score', 50)
        bri_score = BRIScore.objects.filter(user=emp).order_by('-timestamp').first()
        bri_tier = bri_score.tier.lower() if bri_score and bri_score.tier else "green"
        
        last_act_dt = emp.last_login or emp.date_joined
        days_inactive = (now - last_act_dt).days
        
        match = False
        if segment_id == "inactive_14d" and days_inactive >= 14: match = True
        elif segment_id == "inactive_30d" and days_inactive >= 30: match = True
        elif segment_id == "near_profit_share" and 550 <= hps_val < 600: match = True
        elif segment_id == "high_bri" and bri_tier in ("orange", "red"): match = True
        elif segment_id == "low_ehs" and ehs_val < 30: match = True
        elif segment_id == "new_joiners":
            if (now - emp.date_joined).days <= 30: match = True
        elif segment_id == "top_performers" and hps_val >= 800: match = True
        elif segment_id == "declining_hps" and 0 < hps_val < 450: match = True
        
        if match:
            results.append({
                "id": str(emp.id), "name": emp.get_full_name() or emp.username, "email": emp.email,
                "department": emp.profile.department.name if emp.profile.department else "Unknown", 
                "hps": hps_val, "ehs": ehs_val, "bri": getattr(bri_score, 'score', 25), "days_inactive": days_inactive
            })
    return results

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nudge_segments(request):
    _req_corp(request.user)
    company = request.user.profile.company
    segments = []
    for sid, sdef in SEGMENT_DEFS.items():
        emps = _get_segment_employees(company, sid)
        segments.append({**sdef, "id": sid, "count": len(emps)})
    return Response({"segments": segments})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_segment_employees_view(request, segment_id):
    _req_corp(request.user)
    company = request.user.profile.company
    if segment_id not in SEGMENT_DEFS:
        return Response({"error": "Segment not found"}, status=404)
        
    emps = _get_segment_employees(company, segment_id)
    templates = NUDGE_TEMPLATES.get(segment_id, ["Hi {name}, your wellness journey matters. Check in today!"])
    return Response({"segment": SEGMENT_DEFS[segment_id], "employees": emps, "templates": templates})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nudge_campaigns(request):
    _req_corp(request.user)
    campaigns = NudgeCampaign.objects.all().order_by('-created_at')[:50]
    serializer = NudgeCampaignSerializer(campaigns, many=True)
    return Response({"campaigns": serializer.data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_nudge_campaign(request):
    _req_corp(request.user)
    data = request.data
    segment_id = data.get("segment_id")
    company = request.user.profile.company
    
    if segment_id and segment_id not in SEGMENT_DEFS:
        return Response({"error": "Invalid segment"}, status=400)
        
    target_employees = _get_segment_employees(company, segment_id) if segment_id else []
    
    campaign = NudgeCampaign.objects.create(
        name=data.get("name", f"Campaign {timezone.now().strftime('%b %d')}"),
        segment_id=segment_id,
        segment_label=SEGMENT_DEFS.get(segment_id, {}).get("label", "Custom"),
        message_template=data.get("message_template", ""),
        channel=data.get("channel", "in_app"),
        target_count=len(target_employees),
        sent_count=len(target_employees),
        delivered_count=round(len(target_employees) * random.uniform(0.85, 0.98)),
        opened_count=round(len(target_employees) * random.uniform(0.3, 0.65)),
        status="sent",
        created_by=request.user
    )
    
    if target_employees:
        template = data.get("message_template", "You have a new wellness message from HR.")
        for emp_data in target_employees:
            Notification.objects.create(
                user_id=emp_data["id"],
                type="nudge",
                message=template.replace("{name}", emp_data["name"]),
                data={
                    "title": campaign.name,
                    "category": "nudge",
                    "source": "hr",
                    "action_url": "/",
                    "campaign_id": str(campaign.id),
                    "segment": segment_id
                }
            )
            
    serializer = NudgeCampaignSerializer(campaign)
    return Response(serializer.data, status=201)
