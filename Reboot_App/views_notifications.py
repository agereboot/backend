from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Notification, User
import uuid

def create_notification_helper(recipient_id, title, message, category="general", source="system", action_url="", metadata=None):
    """Internal helper to create a notification matching models.py (type/message/data)."""
    try:
        user = User.objects.get(id=recipient_id)
        # We pack title, category, source, action_url into the 'data' JSONField
        data_payload = metadata or {}
        data_payload.update({
            "title": title,
            "category": category,
            "source": source,
            "action_url": action_url
        })
        
        notif = Notification.objects.create(
            user=user,
            type=category, # Using category as 'type'
            message=message,
            data=data_payload
        )
        return notif
    except Exception:
        return None

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """Get notifications for the current user matching legacy FastAPI parity."""
    unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
    limit = int(request.query_params.get('limit', 50))
    
    query = Notification.objects.filter(user=request.user)
    if unread_only:
        query = query.filter(is_read=False)
        
    notifications = query.order_by('-created_at')[:limit]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    # Parity mapping (unfolding 'data' field)
    results = []
    for n in notifications:
        d = n.data or {}
        results.append({
            "id": str(n.id),
            "recipient_id": str(n.user.id),
            "title": d.get("title", "New Notification"),
            "message": n.message,
            "category": n.type,
            "source": d.get("source", "system"),
            "action_url": d.get("action_url", ""),
            "metadata": d,
            "read": n.is_read,
            "created_at": n.created_at.isoformat(),
        })
        
    return Response({
        "notifications": results,
        "unread_count": unread_count
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    """Get unread notification count for badge display parity."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({"unread_count": count})

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a single notification as read parity."""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
        
    notification.is_read = True
    notification.save()
    return Response({"status": "ok"})

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    """Mark all notifications as read parity."""
    updated_count = Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True
    )
    return Response({"marked_count": updated_count})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_notification(request):
    """Create a single notification parity."""
    data = request.data
    notif = create_notification_helper(
        recipient_id=data.get('recipient_id'),
        title=data.get('title'),
        message=data.get('message'),
        category=data.get('category', 'general'),
        source=data.get('source', 'system'),
        action_url=data.get('action_url', ''),
        metadata=data.get('metadata', {})
    )
    if notif:
        return Response({"status": "ok", "id": str(notif.id)})
    return Response({"error": "Failed to create notification"}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_bulk_notifications(request):
    """Create bulk notifications parity."""
    data = request.data
    recipient_ids = data.get('recipient_ids', [])
    count = 0
    for rid in recipient_ids:
        notif = create_notification_helper(
            recipient_id=rid,
            title=data.get('title'),
            message=data.get('message'),
            category=data.get('category', 'nudge'),
            source=data.get('source', 'hr'),
            action_url=data.get('action_url', ''),
            metadata=data.get('metadata', {})
        )
        if notif:
            count += 1
    return Response({"marked_count": count})
