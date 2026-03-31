from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import CompanyContract, PlatformStat, StrategicObjective

def is_hr_admin(user):
    return getattr(user.userprofile, 'role', None) in ['hr_admin', 'super_admin']

def is_cxo(user):
    return getattr(user.userprofile, 'role', None) in ['executive', 'cxo', 'super_admin']

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def corp_dashboard(request):
    """B2B HR Dashboard endpoints."""
    if not is_hr_admin(request.user):
        return Response({"error": "Unauthorized. HR Admin only."}, status=403)
        
    company = getattr(request.user.userprofile, 'company', None)
    if not company:
        return Response({"error": "No company linked to corporate user."}, status=403)
        
    stats = PlatformStat.objects.filter(company=company).order_by('-date')[:30]
    contracts = CompanyContract.objects.filter(company=company)
    
    return Response({
        "company_name": company.name,
        "active_contracts": [{
            "tier": c.plan_tier,
            "max_employees": c.max_employees,
            "end_date": c.end_date,
            "is_active": c.is_active
        } for c in contracts],
        "engagement_metrics": [{
            "metric": s.metric_name,
            "value": s.metric_value,
            "date": s.date
        } for s in stats]
    })
    
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def cxo_strategic_objectives(request):
    """Executive Strategy objectives."""
    if not is_cxo(request.user):
        return Response({"error": "Executive access required."}, status=403)
        
    if request.method == 'GET':
        objectives = StrategicObjective.objects.all().order_by('deadline')
        return Response([{
            "id": str(o.id),
            "title": o.title,
            "department": o.department,
            "target": f"{o.current_value} / {o.target_value} {o.target_metric}",
            "status": o.status,
            "deadline": o.deadline,
            "owner": o.owner.username if o.owner else "Unassigned"
        } for o in objectives])
        
    elif request.method == 'POST':
        obj = StrategicObjective.objects.create(
            title=request.data.get('title'),
            department=request.data.get('department'),
            target_metric=request.data.get('target_metric'),
            target_value=float(request.data.get('target_value', 100)),
            deadline=request.data.get('deadline'),
            owner=request.user
        )
        return Response({"message": "Objective logged", "id": str(obj.id)}, status=201)
