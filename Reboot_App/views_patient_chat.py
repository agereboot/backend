from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime
import uuid

from .models import CCMessage, User, CCAssignment,UserProfile
from .serializers import CCMessageSerializer

# Note: Using CCMessage model which exists in models.py and 
# seems to be the intended chat model.

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_threads(request):
    """Get all chat threads for the current user."""
    user_id = request.user.id
    # In DRF, we can group CCMessage by sender/recipient to simulate threads
    # or use the existing CCMessage logic. 
    # For now, we'll return a list of unique contacts from messages or assignments.
    
    assignments = CCAssignment.objects.filter(member=request.user)
    threads = []
    for ass in assignments:
        hcp = ass.cc
        from django.db.models import Q
        last_msg = CCMessage.objects.filter(
            Q(sender=request.user, recipient=hcp) | Q(sender=hcp, recipient=request.user)
        ).order_by('-sent_at').first()
        
        unread_count = CCMessage.objects.filter(
            sender=hcp, recipient=request.user, read=False
        ).count()
        
        threads.append({
            "id": f"thread_{hcp.id}", # Simulated ID
            "patient_id": request.user.id,
            "hcp_id": hcp.id,
            "hcp_name": hcp.get_full_name() or hcp.username,
            "hcp_role": ass.role,
            "patient_name": request.user.get_full_name() or request.user.username,
            "last_message": last_msg.content[:100] if last_msg else "",
            "last_message_at": last_msg.sent_at.isoformat() if last_msg else timezone.now().isoformat(),
            "unread_count": unread_count,
        })
        
    return Response({"threads": threads})




# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_thread_messages(request, thread_id):
#     print("////")
#     try:
#         print(".........")
#         # If you're passing plain ID like "25"
#         hcp_id = int(thread_id)

#         print('hcp_id',hcp_id)

#         # ✅ FIX HERE
#         hcp_profile = UserProfile.objects.get(user__id=hcp_id)
#         print('hcp_profile',hcp_profile)
#         hcp_user = hcp_profile.user

#     except ValueError:
#         return Response({"error": "Invalid ID"}, status=400)
#     except UserProfile.DoesNotExist:
#         return Response({"error": "UserProfile not found"}, status=404)

#     from django.db.models import Q

#     messages = CCMessage.objects.filter(
#         Q(sender=request.user, recipient=hcp_user) |
#         Q(sender=hcp_user, recipient=request.user)
#     ).order_by('sent_at')[:50]

#     # Mark as read
#     CCMessage.objects.filter(
#         sender=hcp_user,
#         recipient=request.user,
#         read=False
#     ).update(read=True)

#     return Response({
#         "messages": CCMessageSerializer(messages, many=True).data,
#         "thread": {
#             "id": thread_id,
#             "hcp_name": hcp_user.get_full_name() or hcp_user.username
#         }
#     })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_thread_messages(request, thread_id):
    print("////")

    try:
        hcp_id = int(thread_id)
        print('hcp_id', hcp_id)

        # ✅ consistent: using user_id
        hcp_profile = UserProfile.objects.get(user__id=hcp_id)
        hcp_user = hcp_profile.user

    except ValueError:
        return Response({"error": "Invalid ID"}, status=400)
    except UserProfile.DoesNotExist:
        return Response({"error": "UserProfile not found"}, status=404)

    from django.db.models import Q

    # =======================
    # ✅ GET → Fetch Messages
    # =======================
    if request.method == 'GET':
        messages = CCMessage.objects.filter(
            Q(sender=request.user, recipient=hcp_user) |
            Q(sender=hcp_user, recipient=request.user)
        ).order_by('sent_at')[:50]

        # Mark as read
        CCMessage.objects.filter(
            sender=hcp_user,
            recipient=request.user,
            read=False
        ).update(read=True)

        return Response({
            "messages": CCMessageSerializer(messages, many=True).data,
            "thread": {
                "id": thread_id,
                "hcp_name": hcp_user.get_full_name() or hcp_user.username
            }
        })

    # =======================
    # ✅ POST → Send Message
    # =======================
    elif request.method == 'POST':
        content = request.data.get("content", "").strip()

        if not content:
            return Response({"error": "Message cannot be empty"}, status=400)

        msg = CCMessage.objects.create(
            sender=request.user,
            sender_name=request.user.get_full_name() or request.user.username,
            sender_role="patient",
            recipient=hcp_user,  # ✅ correct user object
            content=content,
        )

        return Response({
            "message": "Message sent successfully",
            "data": CCMessageSerializer(msg).data
        }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, thread_id):
    """Send a message in a chat thread."""
    try:
        # hcp_id = thread_id.split('_')[1]
        hcp_id = thread_id
        hcp = UserProfile.objects.get(id=hcp_id)
        # hcp = User.objects.get(id=hcp_id)
    except (IndexError, User.DoesNotExist):
        return Response({"error": "Thread not found"}, status=404)

    content = request.data.get("content", "")
    msg = CCMessage.objects.create(
        sender=request.user,
        sender_name=request.user.get_full_name() or request.user.username,
        sender_role="patient",
        recipient=hcp,
        content=content,
    )
    
    return Response(CCMessageSerializer(msg).data)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    """
    GET /api/patient/messaging/conversations
    Get all messaging conversations for the current user/HCP.
    """
    user = request.user
    
    # Get all messages where user is sender or recipient
    from django.db.models import Q
    messages = CCMessage.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).order_by('-sent_at')[:500]

    # Group by conversation partner
    convos = {}
    for msg in messages:
        # Determine who the other person is
        if msg.sender_id == user.id:
            partner = msg.recipient
            partner_name = msg.recipient_name or (partner.get_full_name() if partner else "Unknown")
        else:
            partner = msg.sender
            partner_name = msg.sender_name or (partner.get_full_name() if partner else "Unknown")
            
        partner_id = str(partner.id) if partner else "system"
        
        if partner_id not in convos:
            convos[partner_id] = {
                "partner_id": partner_id,
                "partner_name": partner_name,
                "last_message": msg.content[:80],
                "last_message_at": msg.sent_at.isoformat(),
                "unread_count": 0,
                "total_messages": 0,
            }
        
        # Increment total messages
        convos[partner_id]["total_messages"] += 1
        
        # Count unread if user is the recipient
        if msg.recipient_id == user.id and not getattr(msg, 'read', True):
            convos[partner_id]["unread_count"] += 1

    # Sort by most recent message time
    conversation_list = sorted(convos.values(), key=lambda c: c["last_message_at"], reverse=True)
    
    return Response({"conversations": conversation_list})

