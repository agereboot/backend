from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Cart, User

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cart(request):
    """GET /api/cart: Returns the user's cart."""
    cart, created = Cart.objects.get_or_create(user=request.user)
    return Response({
        "items": cart.items,
        "total_credits": cart.total_credits
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    """POST /api/cart/add: Adds an item to the cart."""
    data = request.data
    item_id = data.get("intervention_id")
    item_name = data.get("intervention_name", "")
    credits = data.get("credits", 0)
    pillar = data.get("pillar_code", "")
    priority = data.get("priority", "good_to_do")

    if not item_id:
        return Response({"error": "intervention_id is required"}, status=400)

    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items

    # Check for duplicates
    if any(i.get("intervention_id") == item_id for i in items):
        return Response({
            "message": "Already in cart",
            "items": items,
            "total_credits": cart.total_credits
        })

    # Add new item
    items.append({
        "intervention_id": item_id,
        "intervention_name": item_name,
        "credits": credits,
        "pillar_code": pillar,
        "priority": priority,
        "added_at": timezone.now().isoformat()
    })

    cart.items = items
    cart.total_credits = sum(i.get("credits", 0) for i in items)
    cart.save()

    return Response({
        "items": cart.items,
        "total_credits": cart.total_credits
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request):
    """POST /api/cart/remove: Removes an item from the cart."""
    data = request.data
    item_id = data.get("intervention_id")

    if not item_id:
        return Response({"error": "intervention_id is required"}, status=400)

    cart, created = Cart.objects.get_or_create(user=request.user)
    original_items = cart.items
    
    # Filter out the item
    new_items = [i for i in original_items if i.get("intervention_id") != item_id]
    
    cart.items = new_items
    cart.total_credits = sum(i.get("credits", 0) for i in new_items)
    cart.save()

    return Response({
        "items": cart.items,
        "total_credits": cart.total_credits
    })
