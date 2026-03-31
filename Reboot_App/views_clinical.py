from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import PharmacyInventory

def is_hcp(user):
    return getattr(user.userprofile, 'role', None) in ['hcp', 'super_admin']

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_pharmacy(request):
    """Clinical inventory management for lab kits and drugs."""
    if not is_hcp(request.user):
        return Response({"error": "Healthcare Provider access required."}, status=403)
        
    if request.method == 'GET':
        items = PharmacyInventory.objects.all().order_by('name')
        return Response([{
            "id": str(i.id),
            "item_code": i.item_code,
            "name": i.name,
            "category": i.category,
            "stock_quantity": i.quantity,
            "reorder_level": i.reorder_level,
            "restocked_at": i.last_restocked
        } for i in items])
        
    elif request.method == 'POST':
        item, created = PharmacyInventory.objects.update_or_create(
            item_code=request.data.get('item_code'),
            defaults={
                'name': request.data.get('name'),
                'category': request.data.get('category'),
                'quantity': int(request.data.get('quantity', 0)),
                'reorder_level': int(request.data.get('reorder_level', 10)),
                'unit_price': request.data.get('unit_price', 0.0)
            }
        )
        return Response({"message": "Inventory updated", "id": str(item.id)}, status=201)
