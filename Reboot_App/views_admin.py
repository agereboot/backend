from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Avg

from django.contrib.auth.models import User
from .models import (
    PlatformAnnouncement, AuditLog, EmployeeLeave, PayrollRecord, HelpdeskTicket, HPSScore, UserProfile,
    PlatformContent
)

# Optional helper
def is_admin(user):
    return user.is_superuser or getattr(user.userprofile, 'role', None) in ['super_admin', 'hr_admin']

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_stats(request):
    """Aggregate stats across the entire platform for admin board."""
    if not is_admin(request.user):
        return Response({"error": "Unauthorized"}, status=403)
        
    total_users = User.objects.count()
    active_users = UserProfile.objects.filter(role__name='employee').count()
    overall_hps = HPSScore.objects.aggregate(Avg('hps_final'))['hps_final__avg'] or 0.0
    open_tickets = HelpdeskTicket.objects.filter(status='open').count()
    
    return Response({
        "total_users": total_users,
        "active_employees": active_users,
        "average_hps_score": round(overall_hps, 1),
        "open_tickets": open_tickets,
        "timestamp": timezone.now()
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def announcements(request):
    if not is_admin(request.user):
        return Response({"error": "Unauthorized"}, status=403)
        
    if request.method == 'GET':
        annc = PlatformAnnouncement.objects.all().order_by('-created_at')
        return Response([{
            "id": str(a.id),
            "title": a.title,
            "message": a.content, # Aliasing to 'message' for frontend parity
            "type": a.announcement_type,
            "target_role": a.target_role,
            "is_active": a.is_active,
            "is_dismissible": a.is_dismissible,
            "is_pinned": a.is_pinned,
            "starts_at": a.starts_at,
            "expires_at": a.expires_at,
            "action_url": a.action_url,
            "action_label": a.action_label,
            "created_by": a.created_by.username if a.created_by else "System",
            "created_at": a.created_at
        } for a in annc])
        
    elif request.method == 'POST':
        annc = PlatformAnnouncement.objects.create(
            title=request.data.get('title'),
            content=request.data.get('message', ''),
            announcement_type=request.data.get('type', 'info'),
            target_role=request.data.get('target_role', 'all'),
            is_active=request.data.get('is_active', True),
            is_dismissible=request.data.get('is_dismissible', True),
            is_pinned=request.data.get('is_pinned', False),
            starts_at=request.data.get('starts_at', timezone.now()),
            expires_at=request.data.get('expires_at', None),
            action_url=request.data.get('action_url', None),
            action_label=request.data.get('action_label', None),
            created_by=request.user
        )
        AuditLog.objects.create(user=request.user, action="Created Announcement", resource=str(annc.id))
        return Response({"message": "Announcement created!", "id": str(annc.id)}, status=201)

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def announcements_detail(request, ann_id):
    if not is_admin(request.user):
        return Response({"error": "Unauthorized"}, status=403)
        
    try:
        ann = PlatformAnnouncement.objects.get(id=ann_id)
    except PlatformAnnouncement.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
        
    if request.method == 'PUT':
        ann.title = request.data.get('title', ann.title)
        ann.content = request.data.get('message', ann.content)
        ann.announcement_type = request.data.get('type', ann.announcement_type)
        ann.target_role = request.data.get('target_role', ann.target_role)
        ann.is_active = request.data.get('is_active', ann.is_active)
        ann.is_dismissible = request.data.get('is_dismissible', ann.is_dismissible)
        ann.is_pinned = request.data.get('is_pinned', ann.is_pinned)
        ann.expires_at = request.data.get('expires_at', ann.expires_at)
        ann.action_url = request.data.get('action_url', ann.action_url)
        ann.action_label = request.data.get('action_label', ann.action_label)
        ann.save()
        AuditLog.objects.create(user=request.user, action="Updated Announcement", resource=str(ann.id))
        return Response({"message": "Updated"})
        
    elif request.method == 'DELETE':
        ann.delete()
        AuditLog.objects.create(user=request.user, action="Deleted Announcement", resource=str(ann_id))
        return Response({"message": "Deleted"}, status=204)

from django.db.models import Q

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def announcements_active(request):
    """Public employee endpoint. Excludes ones they already dismissed."""
    user = request.user
    role = getattr(user.userprofile, 'role', 'employee')
    now = timezone.now()
    
    # Matching the specific boolean logic written in the FastAPI file:
    active = PlatformAnnouncement.objects.filter(
        is_active=True,
        starts_at__lte=now
    ).filter(
        Q(target_role="all") | Q(target_role=role)
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).exclude(
        dismissed_by=user
    ).order_by('-is_pinned', '-created_at')[:10]
    
    return Response([{
        "id": str(a.id),
        "title": a.title,
        "message": a.content,
        "type": a.announcement_type,
        "action_url": a.action_url,
        "action_label": a.action_label,
        "is_dismissible": a.is_dismissible
    } for a in active])

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def announcements_dismiss(request, ann_id):
    try:
        ann = PlatformAnnouncement.objects.get(id=ann_id)
        if ann.is_dismissible:
            ann.dismissed_by.add(request.user)
            return Response({"message": "Dismissed"})
        else:
            return Response({"error": "Cannot dismiss this announcement"}, status=400)
    except PlatformAnnouncement.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_audit_logs(request):
    if not is_admin(request.user):
        return Response(status=403)
        
    admin_id = request.query_params.get('admin_id', '')
    action_type = request.query_params.get('action_type', '')
    target_type = request.query_params.get('target_type', '')
    date_from = request.query_params.get('date_from', '')
    date_to = request.query_params.get('date_to', '')
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 30))
    
    query = Q()
    if admin_id:
        query &= Q(user_id=admin_id)
    if action_type:
        query &= Q(action=action_type)
    if target_type:
        query &= Q(resource__icontains=target_type)
    if date_from:
        query &= Q(timestamp__gte=date_from)
    if date_to:
        query &= Q(timestamp__lte=date_to)
        
    total = AuditLog.objects.filter(query).count()
    skip = (page - 1) * limit
    
    logs = AuditLog.objects.filter(query).order_by('-timestamp')[skip:skip+limit]
    data = [{
        "user": log.user.username if log.user else "System",
        "action": log.action,
        "resource": log.resource,
        "timestamp": log.timestamp
    } for log in logs]
    
    return Response({
        "logs": data,
        "total": total,
        "page": page,
        "limit": limit
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_action_types(request):
    if not is_admin(request.user):
        return Response(status=403)
        
    types = AuditLog.objects.values_list('action', flat=True).distinct()
    return Response({"action_types": list(types)})

# HRMS
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def leave_management(request):
    if not is_admin(request.user):
        return Response(status=403)
        
    if request.method == 'GET':
        leaves = EmployeeLeave.objects.all().order_by('-created_at')
        return Response([{
            "id": str(l.id),
            "employee": l.employee.username,
            "leave_type": l.leave_type,
            "start": l.start_date,
            "end": l.end_date,
            "status": l.status
        } for l in leaves])
        
    elif request.method == 'POST':
        leave_id = request.data.get('leave_id')
        status_update = request.data.get('status')
        try:
            leave = EmployeeLeave.objects.get(id=leave_id)
            leave.status = status_update
            leave.manager = request.user
            leave.save()
            return Response({"message": "Leave updated"})
        except EmployeeLeave.DoesNotExist:
            return Response({"error": "Leave request not found"}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_records(request):
    if not is_admin(request.user):
        return Response(status=403)
    records = PayrollRecord.objects.all().order_by('-period_start')
    return Response([{
        "id": str(r.id),
        "employee": r.employee.username,
        "period": f"{r.period_start} to {r.period_end}",
        "net_pay": r.net_pay,
        "status": r.status
    } for r in records])

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def helpdesk_tickets(request):
    if request.method == 'GET':
        # Admin sees all, users see their own
        if is_admin(request.user):
            tickets = HelpdeskTicket.objects.all().order_by('-created_at')
        else:
            tickets = HelpdeskTicket.objects.filter(employee=request.user).order_by('-created_at')
        
        return Response([{
            "id": str(t.id),
            "subject": t.subject,
            "status": t.status,
            "category": t.category,
            "created_at": t.created_at
        } for t in tickets])
        
    elif request.method == 'POST':
        ticket = HelpdeskTicket.objects.create(
            employee=request.user,
            subject=request.data.get('subject'),
            description=request.data.get('description'),
            category=request.data.get('category', 'HR')
        )
        return Response({"message": "Ticket created", "id": str(ticket.id)}, status=201)

# ── Bulk Operations ────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_role_change(request):
    """Change role for multiple users at once."""
    if not is_admin(request.user):
        return Response(status=403)
        
    user_ids = request.data.get('user_ids', [])
    new_role_name = request.data.get('new_role')
    
    from .models import Role
    try:
        role_obj = Role.objects.get(name=new_role_name)
    except Role.DoesNotExist:
        return Response({"error": "Invalid role"}, status=400)
        
    modified = UserProfile.objects.filter(user_id__in=user_ids).update(role=role_obj)
    AuditLog.objects.create(user=request.user, action="bulk_role_change", resource=f"Modified {modified} users to {new_role_name}")
    return Response({"message": f"Updated users to role '{new_role_name}'", "modified": modified})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_plan_change(request):
    """Change subscription plan for multiple users at once."""
    if not is_admin(request.user):
        return Response(status=403)
        
    user_ids = request.data.get('user_ids', [])
    new_plan_name = request.data.get('new_plan')
    
    from .models import Plan
    try:
        plan_obj = Plan.objects.get(name=new_plan_name)
    except Plan.DoesNotExist:
        return Response({"error": "Invalid plan"}, status=400)
        
    modified = UserProfile.objects.filter(user_id__in=user_ids).update(plan=plan_obj)
    AuditLog.objects.create(user=request.user, action="bulk_plan_change", resource=f"Modified {modified} users to plan {new_plan_name}")
    return Response({"message": f"Updated users to plan '{new_plan_name}'", "modified": modified})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_status_change(request):
    """Activate or deactivate multiple users at once."""
    if not is_admin(request.user):
        return Response(status=403)
        
    user_ids = request.data.get('user_ids', [])
    new_status = request.data.get('new_status')
    
    if new_status not in ["active", "deactivated"]:
        return Response({"error": "Invalid status. Must be 'active' or 'deactivated'"}, status=400)
        
    is_active_bool = (new_status == "active")
    modified = User.objects.filter(id__in=user_ids).update(is_active=is_active_bool)
    AuditLog.objects.create(user=request.user, action="bulk_status_change", resource=f"Modified {modified} users to {new_status}")
    return Response({"message": f"Updated users to status '{new_status}'", "modified": modified})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_users_csv(request):
    """Export all users as CSV data."""
    if not is_admin(request.user):
        return Response(status=403)
        
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="users_export_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(["id", "username", "email", "role", "plan", "status", "joined_at"])
    
    # Query via select_related to prevent massive N+1 queries during export
    users = User.objects.select_related('userprofile__role', 'userprofile__plan').all()
    for u in users:
        writer.writerow([
            u.id,
            u.username,
            u.email,
            u.userprofile.role.name if hasattr(u, 'userprofile') and u.userprofile.role else "",
            u.userprofile.plan.name if hasattr(u, 'userprofile') and u.userprofile.plan else "",
            "active" if u.is_active else "deactivated",
            u.date_joined.isoformat()
        ])
        
    return response

# ── Content Management System (CMS) ─────────────────────────────────────────
from .models import PlatformContent

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def content_list_create(request):
    if not is_admin(request.user):
        return Response(status=403)
        
    if request.method == 'GET':
        c_type = request.query_params.get('content_type', '')
        status_filter = request.query_params.get('status', '')
        search = request.query_params.get('search', '')
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))
        
        query = Q()
        if c_type:
            query &= Q(content_type=c_type)
        if status_filter:
            query &= Q(status=status_filter)
        if search:
            query &= (Q(title__icontains=search) | Q(body__icontains=search))
            
        total = PlatformContent.objects.filter(query).count()
        skip = (page - 1) * limit
        items = PlatformContent.objects.filter(query).order_by('-updated_at')[skip:skip+limit]
        
        return Response({
            "content": [{
                "id": str(i.id),
                "title": i.title,
                "content_type": i.content_type,
                "status": i.status,
                "target_roles": i.target_roles,
                "author": i.author.username if i.author else "",
                "updated_at": i.updated_at
            } for i in items],
            "total": total,
            "page": page,
            "limit": limit
        })
        
    elif request.method == 'POST':
        ctype = request.data.get('content_type', 'health_tip')
        status_val = request.data.get('status', 'draft')
        
        item = PlatformContent.objects.create(
            title=request.data.get('title'),
            body=request.data.get('body'),
            content_type=ctype,
            category=request.data.get('category', ''),
            tags=request.data.get('tags', []),
            target_roles=request.data.get('target_roles', ['all']),
            status=status_val,
            featured_image_url=request.data.get('featured_image_url'),
            author=request.user,
            published_at=timezone.now() if status_val == 'published' else None
        )
        AuditLog.objects.create(user=request.user, action="content_created", resource=str(item.id))
        return Response({"message": "Content created", "id": str(item.id)}, status=201)

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def content_detail(request, content_id):
    if not is_admin(request.user):
        return Response(status=403)
        
    try:
        item = PlatformContent.objects.get(id=content_id)
    except PlatformContent.DoesNotExist:
        return Response({"error": "Content not found"}, status=404)
        
    if request.method == 'PUT':
        old_status = item.status
        item.title = request.data.get('title', item.title)
        item.body = request.data.get('body', item.body)
        item.content_type = request.data.get('content_type', item.content_type)
        item.category = request.data.get('category', item.category)
        item.tags = request.data.get('tags', item.tags)
        item.target_roles = request.data.get('target_roles', item.target_roles)
        item.status = request.data.get('status', item.status)
        item.featured_image_url = request.data.get('featured_image_url', item.featured_image_url)
        
        if item.status == 'published' and old_status != 'published':
            item.published_at = timezone.now()
            
        item.save()
        AuditLog.objects.create(user=request.user, action="content_updated", resource=str(item.id))
        return Response({"message": "Content updated"})
        
    elif request.method == 'DELETE':
        item.delete()
        AuditLog.objects.create(user=request.user, action="content_deleted", resource=content_id)
        return Response({"message": "Content deleted"}, status=204)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_published_content(request):
    """Public endpoint for employees to consume published content targeted to them."""
    role = getattr(request.user.userprofile, 'role', None)
    role_name = role.name if role else 'employee'
    c_type = request.query_params.get('content_type', 'health_tip')
    limit = int(request.query_params.get('limit', 10))
    
    query = Q(status='published', content_type=c_type)
    # Target Roles is a JSON array; match if it contains the exact role name OR "all"
    query &= (Q(target_roles__contains=role_name) | Q(target_roles__contains='all'))
    
    items = PlatformContent.objects.filter(query).order_by('-published_at')[:limit]
    
    # Increment view counts safely natively in DB
    from django.db.models import F
    if items.exists():
        PlatformContent.objects.filter(id__in=[i.id for i in items]).update(view_count=F('view_count') + 1)
        
    return Response({"content": [{
        "id": str(i.id),
        "title": i.title,
        "body": i.body,
        "category": i.category,
        "featured_image_url": i.featured_image_url,
        "published_at": i.published_at
    } for i in items]})

# ── Corporate / B2B Administration ──────────────────────────────────────────
from .models import Company, CompanyContract
from django.db.models import Count, Avg

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_corporates(request):
    """List or Create Corporate Accounts"""
    if not is_admin(request.user):
        return Response(status=403)
        
    if request.method == 'GET':
        search = request.query_params.get('search', '')
        status_filter = request.query_params.get('status', '')
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))
        
        query = Q()
        if search:
            query &= Q(name__icontains=search)
        if status_filter:
            is_active = (status_filter.lower() == 'active')
            query &= Q(status=is_active)
            
        total = Company.objects.filter(query).count()
        skip = (page - 1) * limit
        
        # Native PostgreSQL Aggregation for Employee Enrollment Count
        companies = Company.objects.filter(query).annotate(
            enrolled_employees=Count('userprofile')
        ).order_by('-created_at')[skip:skip+limit]
        
        return Response({
            "corporates": [{
                "id": str(c.id),
                "company_name": c.name,
                "industry": getattr(c, 'industry', 'Technology'),
                "status": "active" if c.status else "inactive",
                "enrolled_employees": c.enrolled_employees,
                "created_at": c.created_at
            } for c in companies],
            "total": total,
            "page": page,
            "limit": limit
        })
        
    elif request.method == 'POST':
        from django.db import transaction
        
        name = request.data.get('company_name')
        if Company.objects.filter(name=name).exists():
            return Response({"error": "Company name already exists"}, status=400)
            
        with transaction.atomic():
            company = Company.objects.create(
                name=name,
                industry=request.data.get('industry', 'Technology'),
                admin_email=request.data.get('admin_email', ''),
                status=True
            )
            
            # Formally generate their subscription contract
            import datetime
            start_str = request.data.get('contract_start')
            try:
                start_date = datetime.datetime.fromisoformat(start_str).date() if start_str else timezone.now().date()
            except ValueError:
                start_date = timezone.now().date()
                
            CompanyContract.objects.create(
                company=company,
                plan_tier=request.data.get('plan', 'velocity_circuit'),
                start_date=start_date,
                end_date=start_date + datetime.timedelta(days=365), # Default 1 yr
                max_employees=request.data.get('license_count', 100),
                pricing_model='per_seat',
                is_active=True
            )
            
        AuditLog.objects.create(user=request.user, action="corporate_created", resource=str(company.id))
        return Response({
            "corporate": {
                "id": str(company.id),
                "company_name": company.name,
                "industry": company.industry,
                "admin_email": company.admin_email
            }
        }, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_corporate_detail(request, corp_id):
    """Detailed corporate analytics view"""
    if not is_admin(request.user):
        return Response(status=403)
        
    try:
        corp = Company.objects.get(id=corp_id)
    except Company.DoesNotExist:
        return Response({"error": "Corporate account not found"}, status=404)
        
    # Natively gather employees mapped to this corporate profile
    employees = User.objects.filter(profile__company=corp).select_related('profile')
    
    # Natively calculate the Average HPS Score across the entire company flawlessly
    from .models import HPSScore
    avg_data = HPSScore.objects.filter(user__in=employees).aggregate(avg_score=Avg('total_score'))
    avg_score = round(avg_data['avg_score']) if avg_data['avg_score'] else 0
    
    contract = corp.contracts.first()
    
    return Response({
        "corporate": {
            "id": str(corp.id),
            "company_name": corp.name,
            "industry": corp.industry,
            "admin_email": corp.admin_email,
            "status": "active" if corp.status else "inactive",
            "plan": contract.plan_tier if contract else "none",
            "license_count": contract.max_employees if contract else 0
        },
        "enrolled_employees": employees.count(),
        "avg_hps_score": avg_score,
        "employees": [{
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "role": u.profile.role.name if getattr(u.profile, 'role', None) else ""
        } for u in employees[:50]]
    })

# ── Financial / Revenue Operations ──────────────────────────────────────────
from .models import Plan

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_overview(request):
    """Dynamically calculates MRR reading organically from the Plan definitions table."""
    if not is_admin(request.user):
        return Response(status=403)
        
    plans = Plan.objects.all()
    
    plan_counts = {}
    total_mrr = 0
    paid_subscribers = 0
    total_subscribers = 0
    
    plan_revenue = {}
    
    for plan in plans:
        # PostgreSQL Count optimization
        count = UserProfile.objects.filter(plan=plan).count()
        
        monthly_cost = float(plan.price) / 12 if plan.price else 0
        monthly_rev = round(monthly_cost * count)
        
        plan_counts[plan.name] = count
        plan_revenue[plan.name] = {"count": count, "monthly_revenue": monthly_rev}
        
        total_mrr += monthly_rev
        total_subscribers += count
        if float(plan.price) > 0:
            paid_subscribers += count
            
    # Corporate contracts
    contracts = CompanyContract.objects.filter(is_active=True).select_related('company')
            
    return Response({
        "mrr": total_mrr,
        "arr": total_mrr * 12,
        "plan_breakdown": plan_revenue,
        "total_subscribers": total_subscribers,
        "paid_subscribers": paid_subscribers,
        "corporate_contracts": contracts.count(),
        "contracts": [{
            "company_name": c.company.name,
            "plan_tier": c.plan_tier,
            "end_date": c.end_date
        } for c in contracts[:10]]
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_details(request):
    """Detailed pricing limits directly queried from the Database."""
    if not is_admin(request.user):
        return Response(status=403)
        
    plans = Plan.objects.all()
    results = []
    
    for plan in plans:
        count = UserProfile.objects.filter(plan=plan).count()
        price = float(plan.price)
        
        results.append({
            "code": plan.name,
            "name": plan.name.replace("_", " ").title(),
            "annual_price_inr": price,
            "monthly_price_inr": round(price / 12),
            "user_count": count,
            "monthly_revenue": round((price / 12) * count)
        })
        
    return Response({"plans": results})

# ── HPS Monitor / Medical Analytics ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hps_score_distribution(request):
    """Score distribution analytics across all users."""
    if not is_admin(request.user):
        return Response(status=403)
        
    # Get distinct latest scores
    from .models import HPSScore
    scores = HPSScore.objects.order_by('user_id', '-timestamp')
    
    latest_scores = []
    seen = set()
    for s in scores:
        if s.user_id not in seen:
            seen.add(s.user_id)
            latest_scores.append(s.hps_final)
            
    # Compute buckets
    buckets = {i: 0 for i in range(10)}
    for val in latest_scores:
        if 0 <= val <= 1000:
            idx = int(val // 100)
            if idx == 10: idx = 9
            buckets[idx] += 1
            
    dist = []
    for i in range(10):
        start = i * 100
        dist.append({"range": f"{start}-{start+99}", "count": buckets[i]})
        
    return Response({"distribution": dist})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hps_pillar_averages(request):
    """Platform-wide average per HPS pillar."""
    if not is_admin(request.user):
        return Response(status=403)
        
    from .models import HPSScore
    scores = HPSScore.objects.order_by('user_id', '-timestamp')
    
    seen = set()
    pillar_totals = {"bio": 0, "fit": 0, "cog": 0, "slp": 0, "beh": 0}
    count = 0
    
    for s in scores:
        if s.user_id not in seen:
            seen.add(s.user_id)
            count += 1
            pillars = s.pillars or {}
            pillar_totals["bio"] += float(pillars.get("biological_resilience", 0))
            pillar_totals["fit"] += float(pillars.get("physical_fitness", 0))
            pillar_totals["cog"] += float(pillars.get("cognitive_health", 0))
            pillar_totals["slp"] += float(pillars.get("sleep_recovery", 0))
            pillar_totals["beh"] += float(pillars.get("behaviour_lifestyle", 0))
            
    if count == 0:
        return Response({"pillars": {}, "user_count": 0})
        
    return Response({
        "pillars": {
            "Biological Resilience": round(pillar_totals["bio"] / count, 1),
            "Physical Fitness": round(pillar_totals["fit"] / count, 1),
            "Cognitive Health": round(pillar_totals["cog"] / count, 1),
            "Sleep & Recovery": round(pillar_totals["slp"] / count, 1),
            "Behaviour & Lifestyle": round(pillar_totals["beh"] / count, 1),
        },
        "user_count": count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hps_calculation_logs(request):
    """Recent HPS calculation logs."""
    if not is_admin(request.user):
        return Response(status=403)
        
    from .models import HPSScore
    logs = HPSScore.objects.select_related('user').order_by('-timestamp')[:50]
    
    return Response({"logs": [{
        "user_id": str(lg.user_id),
        "username": lg.user.username,
        "total_score": lg.hps_final,
        "computed_at": lg.timestamp,
        "domain_scores": lg.pillars
    } for lg in logs]})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def low_score_alerts(request):
    """Users with HPS below 400."""
    if not is_admin(request.user):
        return Response(status=403)
        
    from .models import HPSScore
    scores = HPSScore.objects.filter(hps_final__lt=400).select_related('user').order_by('-timestamp')
    
    alerts = []
    seen = set()
    
    for doc in scores:
        if doc.user_id not in seen:
            seen.add(doc.user_id)
            alerts.append({
                "user_id": str(doc.user_id),
                "user_name": f"{doc.user.first_name} {doc.user.last_name}".strip() or doc.user.username,
                "score": doc.hps_final,
                "computed_at": doc.timestamp
            })
            if len(alerts) >= 50:
                break
                
    return Response({"alerts": alerts})


# ── HRMS / Asset Tracking Operations ─────────────────────────────────────────

from .models import Asset
import uuid

ASSET_TYPES = ["laptop", "monitor", "keyboard", "mouse", "headset", "phone",
               "desk", "chair", "access_card", "software_license", "other"]
ASSET_STATUSES = ["available", "assigned", "under_repair", "retired", "lost"]

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_assets(request):
    """List or Create IT Assets"""
    if not is_admin(request.user):
        return Response(status=403)
        
    if request.method == 'GET':
        search = request.query_params.get('search', '')
        asset_type = request.query_params.get('asset_type', '')
        status_filter = request.query_params.get('status', '')
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 30))
        
        query = Q()
        if asset_type:
            query &= Q(asset_type=asset_type)
        if status_filter:
            query &= Q(status=status_filter)
        if search:
            query &= (
                Q(serial_number__icontains=search) |
                Q(brand__icontains=search) |
                Q(model__icontains=search) |
                Q(asset_tag__icontains=search)
            )
            
        total = Asset.objects.filter(query).count()
        skip = (page - 1) * limit
        
        assets = Asset.objects.filter(query).order_by('-created_at')[skip:skip+limit]
        
        return Response({
            "assets": [{
                "id": str(a.id),
                "asset_tag": a.asset_tag,
                "asset_type": a.asset_type,
                "brand": a.brand,
                "model": a.model,
                "serial_number": a.serial_number,
                "status": a.status,
                "assigned_to": str(a.assigned_to_id) if a.assigned_to else None,
                "assigned_to_name": a.assigned_to_name,
                "assigned_at": a.assigned_at
            } for a in assets],
            "total": total,
            "page": page,
            "limit": limit
        })
        
    elif request.method == 'POST':
        atype = request.data.get('asset_type')
        if atype not in ASSET_TYPES:
            return Response({"error": f"Invalid asset type. Valid: {ASSET_TYPES}"}, status=400)
            
        count = Asset.objects.count() + 1
        tag = f"AST-{count:04d}"
        
        asset = Asset.objects.create(
            asset_tag=tag,
            asset_type=atype,
            brand=request.data.get('brand', ''),
            model=request.data.get('model', ''),
            serial_number=request.data.get('serial_number', ''),
            purchase_date=request.data.get('purchase_date', ''),
            purchase_cost=float(request.data.get('purchase_cost', 0.0)),
            warranty_expiry=request.data.get('warranty_expiry', ''),
            status="available",
            notes=request.data.get('notes', ''),
            history=[{"action": "created", "date": timezone.now().isoformat()}]
        )
        
        AuditLog.objects.create(user=request.user, action="asset_created", resource=str(asset.id))
        return Response({"asset": {"id": str(asset.id), "asset_tag": asset.asset_tag, "asset_type": asset.asset_type}}, status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_asset(request, asset_id):
    if not is_admin(request.user): return Response(status=403)
    
    try:
        asset = Asset.objects.get(id=asset_id)
        emp = User.objects.get(id=request.data.get('employee_id'))
    except (Asset.DoesNotExist, User.DoesNotExist):
        return Response({"error": "Asset or Employee not found"}, status=404)
        
    if asset.status == 'assigned':
        return Response({"error": "Asset already assigned."}, status=400)
        
    emp_name = f"{emp.first_name} {emp.last_name}".strip() or emp.username
    asset.status = "assigned"
    asset.assigned_to = emp
    asset.assigned_to_name = emp_name
    asset.assigned_at = timezone.now()
    asset.history.append({"action": "assigned", "to": str(emp.id), "to_name": emp_name, "at": timezone.now().isoformat()})
    asset.save()
    
    AuditLog.objects.create(user=request.user, action="asset_assigned", resource=str(asset.id))
    return Response({"message": "Asset assigned"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unassign_asset(request, asset_id):
    if not is_admin(request.user): return Response(status=403)
    
    try:
        asset = Asset.objects.get(id=asset_id)
    except Asset.DoesNotExist:
        return Response(status=404)
        
    asset.history.append({"action": "unassigned", "from": str(asset.assigned_to_id), "from_name": asset.assigned_to_name, "at": timezone.now().isoformat()})
    asset.status = "available"
    asset.assigned_to = None
    asset.assigned_to_name = None
    asset.assigned_at = None
    asset.save()
    
    return Response({"message": "Asset unassigned"})

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_asset_status(request, asset_id):
    if not is_admin(request.user): return Response(status=403)
    
    status = request.query_params.get('status')
    if status not in ASSET_STATUSES:
        return Response({"error": "Invalid status"}, status=400)
        
    try:
        asset = Asset.objects.get(id=asset_id)
        asset.status = status
        asset.save()
        return Response({"message": f"Asset status updated to {status}"})
    except Asset.DoesNotExist:
        return Response(status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def asset_summary(request):
    """Instant postgres native asset aggregation."""
    if not is_admin(request.user): return Response(status=403)
    
    from django.db.models import Count
    metrics = Asset.objects.values('asset_type', 'status').annotate(count=Count('id'))
    
    summary = {}
    for m in metrics:
        t, s = m['asset_type'], m['status']
        if t not in summary: summary[t] = {}
        summary[t][s] = m['count']
        
    total = Asset.objects.count()
    assigned = Asset.objects.filter(status="assigned").count()
    available = Asset.objects.filter(status="available").count()
    
    return Response({
        "total": total,
        "assigned": assigned,
        "available": available,
        "by_type": summary
    })


# ── HRMS / Core Employee Tracking ──────────────────────────────────────────

from .models import UserProfile, Department, LeaveBalance

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_hrms_employees(request):
    """Admin-level HRMS employee onboarding and index"""
    if not is_admin(request.user): return Response(status=403)
    
    if request.method == 'GET':
        search = request.query_params.get('search', '')
        department = request.query_params.get('department', '')
        status = request.query_params.get('status', '')
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))
        
        query = Q(profile__isnull=False)
        if search:
            query &= (Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search))
        if department:
            query &= Q(profile__department__name=department)
        if status:
            pass # Handle status logic if bound to active flag
            
        total = User.objects.filter(query).count()
        skip = (page - 1) * limit
        users = User.objects.filter(query).select_related('profile', 'profile__department', 'profile__manager').order_by('-date_joined')[skip:skip+limit]
        
        return Response({
            "employees": [{
                "id": str(u.id),
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "department": u.profile.department.name if u.profile.department else None,
                "designation": getattr(u.profile, 'designation', 'Employee'),
                "employment_type": getattr(u.profile, 'employment_type', 'full_time'),
                "manager": f"{u.profile.manager.first_name} {u.profile.manager.last_name}".strip() if u.profile.manager else None,
                "status": "active" if u.is_active else "offboarded",
                "date_of_joining": u.profile.date_of_joining,
            } for u in users],
            "total": total,
            "page": page,
            "limit": limit
        })
        
    elif request.method == 'POST':
        # Handles user creation manually
        from django.contrib.auth.hashers import make_password
        
        email = request.data.get('email')
        if User.objects.filter(email=email).exists():
            return Response({"error": "Employee with this email already exists"}, status=400)
            
        u = User.objects.create(
            username=email.split('@')[0] + str(uuid.uuid4())[:4],
            email=email,
            first_name=request.data.get('first_name', ''),
            last_name=request.data.get('last_name', ''),
            password=make_password("TempPassword123!")
        )
        
        dept, _ = Department.objects.get_or_create(name=request.data.get('department', 'Engineering'))
        
        manager_id = request.data.get('manager_id')
        manager = User.objects.get(id=manager_id) if manager_id else None
        
        profile = UserProfile.objects.create(
            user=u,
            department=dept,
            phone_number=request.data.get('phone', ''),
            employment_type=request.data.get('employment_type', 'full_time'),
            salary_annual=float(request.data.get('salary_annual', 0.0)),
            salary_currency=request.data.get('salary_currency', 'INR'),
            manager=manager,
            skills=request.data.get('skills', [])
        )
        
        LeaveBalance.objects.create(
            user=u,
            casual_leave={"total": 12, "used": 0, "balance": 12},
            sick_leave={"total": 10, "used": 0, "balance": 10},
            earned_leave={"total": 15, "used": 0, "balance": 15},
            comp_off={"total": 0, "used": 0, "balance": 0}
        )
        
        return Response({"employee": {"id": str(u.id), "email": u.email}}, status=201)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def manage_hrms_employee_detail(request, emp_id):
    if not is_admin(request.user): return Response(status=403)
    
    try:
        emp = User.objects.select_related('profile', 'profile__department', 'profile__manager').get(id=emp_id)
    except User.DoesNotExist:
        return Response(status=404)
        
    if request.method == 'GET':
        manager = emp.profile.manager
        reports = User.objects.filter(profile__manager=emp).only('id', 'first_name', 'last_name')
        
        try:
            lb = LeaveBalance.objects.get(user=emp)
            leave_balance = {
                "casual_leave": lb.casual_leave,
                "sick_leave": lb.sick_leave,
                "earned_leave": lb.earned_leave
            }
        except LeaveBalance.DoesNotExist:
            leave_balance = {}
            
        assets = Asset.objects.filter(assigned_to=emp, status="assigned")
        
        return Response({
            "employee": {
                "id": str(emp.id),
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "email": emp.email,
                "department": emp.profile.department.name if emp.profile.department else None,
                "salary_annual": emp.profile.salary_annual,
                "employment_type": emp.profile.employment_type,
                "skills": emp.profile.skills,
                "status": "active" if emp.is_active else "offboarded"
            },
            "manager": {"id": str(manager.id), "name": f"{manager.first_name} {manager.last_name}".strip()} if manager else None,
            "direct_reports": [{"id": str(r.id), "name": f"{r.first_name} {r.last_name}".strip()} for r in reports],
            "leave_balance": leave_balance,
            "assigned_assets": [{"id": str(a.id), "tag": a.asset_tag, "type": a.asset_type} for a in assets]
        })
        
    elif request.method == 'PUT':
        # Handle field mutations
        data = request.data
        if 'first_name' in data: emp.first_name = data['first_name']
        if 'last_name' in data: emp.last_name = data['last_name']
        if 'status' in data:
            emp.is_active = (data['status'] != 'offboarded')
            if not emp.is_active:
                emp.profile.offboard_date = timezone.now().date()
                emp.profile.offboard_reason = data.get('offboard_reason', '')
        
        if 'department' in data:
            dept, _ = Department.objects.get_or_create(name=data['department'])
            emp.profile.department = dept
            
        if 'manager_id' in data:
            try:
                emp.profile.manager = User.objects.get(id=data['manager_id'])
            except User.DoesNotExist:
                pass
                
        if 'salary_annual' in data: emp.profile.salary_annual = float(data['salary_annual'])
        if 'employment_type' in data: emp.profile.employment_type = data['employment_type']
        if 'skills' in data: emp.profile.skills = data['skills']
        
        emp.save()
        emp.profile.save()
        
        return Response({"message": "Successfully updated profile"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_hrms_departments(request):
    """Aggregate department headcounts"""
    if not is_admin(request.user): return Response(status=403)
    
    from django.db.models import Count
    # PostgreSQL group by
    metrics = UserProfile.objects.filter(user__is_active=True).values('department__name').annotate(headcount=Count('id')).order_by('-headcount')
    
    depts = []
    for m in metrics:
        name = m['department__name'] or "Unassigned"
        depts.append({"name": name, "headcount": m['headcount']})
        
    return Response({"departments": depts})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_hrms_org_chart(request):
    """Build the full recursive org tree"""
    if not is_admin(request.user): return Response(status=403)
    
    employees = User.objects.filter(is_active=True).select_related('profile', 'profile__department')
    
    emp_map = {}
    for e in employees:
        emp_map[e.id] = {
            "id": str(e.id),
            "first_name": e.first_name,
            "last_name": e.last_name,
            "department": e.profile.department.name if getattr(e.profile, 'department', None) else None,
            "designation": getattr(e.profile, 'designation', 'Employee'),
            "manager_id": e.profile.manager_id if getattr(e.profile, 'manager_id', None) else None,
            "children": []
        }
        
    roots = []
    for eid, data in emp_map.items():
        mid = data.get("manager_id")
        if mid and mid in emp_map:
            emp_map[mid]["children"].append(data)
        else:
            roots.append(data)
            
    return Response({"org_chart": roots, "total_employees": len(employees)})
